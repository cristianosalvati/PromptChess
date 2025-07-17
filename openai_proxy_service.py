import os
import atexit
import json
import logging
import tiktoken
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from openai import OpenAI, RateLimitError, OpenAIError

# Carica le variabili d'ambiente
dotenv_path = os.getenv('DOTENV_PATH', None)
if dotenv_path:
    load_dotenv(dotenv_path)
else:
    load_dotenv()

# Instanzia il client OpenAI
# api_key = "sk-proj-...."
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("OPENAI_API_KEY not found. Check the .env file or environment variables.")
client = OpenAI(api_key=api_key)

# Configura il logger
logging.basicConfig(level=logging.WARN)
logger = logging.getLogger(__name__)

# Definisci la lunghezza massima del contesto per ciascun modello
DEFAULT_MAX_TOKENS = 16384  # Valore di default se il modello non è specificato
MODEL_MAX_TOKENS = {
    "gpt-3.5-turbo": 32768,
    "o1-mini": 32768,
    "o3-mini": 32768,
    "o3": 32768,
    "o4-mini": 32768,
    "gpt-4": 32768,      # o 32768 se usi la variante 32k
    "gpt-4-turbo": 32768,
    "gpt-4o": 32768,
    "gpt-4o-mini": 32768,
    "gpt-4.1": 32768,
    "gpt-4.1-mini": 32768,
    "gpt-4.1-nano": 32768
    # aggiungi altri modelli se serve…
}

def count_message_tokens(messages: list[dict], model: str) -> int:
    """
    Conta i token usati dalla lista di messages, includendo qualche overhead per
    i metadati dei messaggi (13 token per messaggio su cl100k_base).
    """
    enc = tiktoken.encoding_for_model(model)
    total = 0
    for m in messages:
        # conteggia i token del content
        total += len(enc.encode(m["content"]))
        # aggiungi overhead fisso per ruolo + delimitatori
        total += 13
    return total

def dynamic_max_tokens(model: str, messages: list[dict], margin: int = 100) -> int:
    """
    Restituisce quanti token puoi allocare per la risposta:
      max = modello.contesto_max - token_usati - margin
    Assicura almeno un valore minimo di 0.
    """
    try:
        used = count_message_tokens(messages, model)
    except Exception:
        # stima approssimativa: 1 token ≃ 4 caratteri
        total_chars = sum(len(m.get("content", "")) for m in messages)
        used = total_chars // 4 + len(messages) * 2  # +2 token di overhead per messaggio

    context_max = MODEL_MAX_TOKENS.get(model, DEFAULT_MAX_TOKENS)
    available = context_max - used - margin
    return max(0, available)

class ChatSession:

    def __init__(self, client, max_history=100):
        self.client = client
        # Messaggio di sistema iniziale
        self.messages = []
        # Numero massimo di messaggi (escluso il system)
        self.max_history = max_history

        self.system_message_count = 0

    def has_message(self, role: str, content: str) -> bool:
        """
        Verifica se un messaggio con il dato role e content è già presente nella storia.
        """
        return any(
            m.get("role") == role and m.get("content") == content
            for m in self.messages
        )
    
    def put_message(self, role: str, content: str):
        # Aggiunge un messaggio e mantiene la storia entro max_history
        self.messages.append({"role": role, "content": content})
        # Rimuovi il messaggio più vecchio (dopo il system) se superiamo la storia massima
        if len(self.messages) - 1 > self.max_history:
            # pop l'elemento immediatamente dopo il system
            self.messages.pop(self.system_message_count + 1)
    
    def prepend_message(self, role: str, content: str):
        # Aggiunge un messaggio subito dopo il system (in testa alla storia)
        # Mantiene il sistema al primo posto
        self.messages.insert(1, {"role": role, "content": content})
        # Se eccede la history, rimuove l'ultimo
        if len(self.messages) - 1 > self.max_history:
            self.messages.pop()

    def pop_last_message(self):
        # Rimuove l'ultimo messaggio (se non è il system)
        if len(self.messages) > 1:
            return self.messages.pop()
        return None
    
    def pop_last_assistant(self):
        """
        Rimuove e restituisce l'ultimo messaggio con role 'assistant'.
        Se non trova messaggi assistant (oltre al system), ritorna None.
        """
        # scorri la lista al contrario alla ricerca di un assistant
        for idx in range(len(self.messages) - 1, 0, -1):
            if self.messages[idx]["role"] == "assistant":
                return self.messages.pop(idx)
        return None
    
    
    def get_last_assistant(self):
        """
        Rimuove e restituisce l'ultimo messaggio con role 'assistant'.
        Se non trova messaggi assistant (oltre al system), ritorna None.
        """
        # scorri la lista al contrario alla ricerca di un assistant
        for idx in range(len(self.messages) - 1, 0, -1):
            if self.messages[idx]["role"] == "assistant":
                return self.messages[idx]
        return None
    
    def get_last_user(self):
        """
        Rimuove e restituisce l'ultimo messaggio con role 'user'.
        Se non trova messaggi user (oltre al system), ritorna None.
        """
        # scorri la lista al contrario alla ricerca di un user
        for idx in range(len(self.messages) - 1, 0, -1):
            if self.messages[idx]["role"] == "user":
                return self.messages[idx]
        return None

    def add_initial_system(self, content: str, force : bool) -> bool:
        """
        Aggiunge un messaggio di sistema solo se NON sono ancora stati inviati
        né messaggi user né assistant.
        Ritorna True se il messaggio è stato aggiunto, False altrimenti.
        """
        # cerca in messages eventuali role 'user' o 'assistant'
        has_interaction = any(m["role"] in ("user", "assistant") for m in self.messages)
        if not has_interaction:
            # Se non ci sono interazioni, aggiunge il system solo se non esiste già
            if not self.has_message("system", content):
                self.messages.append({"role": "system", "content": content})
            return True
        else:
            if force:
                # Se forzato, rimuove tutti i messaggi precedenti
                self.messages.clear()
                # Aggiunge il nuovo system come primo messaggio
                self.messages.append({"role": "system", "content": content})
                return True
        return False

    def chat(self, prompt: str, model: str = "gpt-4.1-nano",
             temperature: float = 0.5, margin: int = 100) -> str:
        
        if self.system_message_count == 0:
            raise RuntimeError("Nessun messaggio di sistema iniziale. Usa /chat/init per aggiungerne uno.")

        # 1) append utente
        last_user = self.get_last_user()
        if last_user is not None and last_user.get('content') == prompt:
            print("[DEBUG] Messaggio utente già presente, non lo aggiungo.")
        else:
            self.put_message("user", prompt)

        # 2) calcola max_tokens in base alla storia
        max_tokens = dynamic_max_tokens(model, self.messages, margin=margin)

        print(f"[DEBUG] Token disponibili per la risposta: {max_tokens}")
       
        if max_tokens <= 0:
            raise RuntimeError("Max tokens exceeded.")

        # Chiama l'API
        completion = self.client.chat.completions.create(
            model=model,
            messages=self.messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        answer = completion.choices[0].message.content
        
        # Aggiunge la risposta del modello
        self.put_message("assistant", answer)

        print(f"[DEBUG] dimensione chat: {len(chat_session.messages)}")
        return answer

# Funzione per salvare la cronologia a chiusura
def dump_history_on_exit():
    try:
        logs_dir = 'resources/logs'
        os.makedirs(logs_dir, exist_ok=True)
        now = datetime.now().strftime('%Y%m%d-%H%M%S-%f')[:-3]
        filename = f"history_{now}.json"
        path = os.path.join(logs_dir, filename)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(chat_session.messages, f, ensure_ascii=False, indent=2)
        logger.info(f"Cronologia chat salvata in {path}")
    except Exception as e:
        logger.error(f"Errore salvando cronologia: {e}")

# Registra il dump alla chiusura del programma
atexit.register(dump_history_on_exit)

# Instanzia e configura Flask
chat_session = ChatSession(client)
app = Flask(__name__, template_folder='webapp/templates', static_folder='webapp/static')
CORS(app, resources={r"/*": {"origins": "*"}})

@app.route("/chat", methods=["POST"])
def chat():
    # TODO : aggiungi validazione del modello e temperatura
    data = request.get_json() or {}
    prompt = data.get("prompt", "").strip()
    model = data.get("model", None)
    temperature = data.get("temperature", None)

    if not prompt:
        return jsonify({"error": "Prompt mancante"}), 400

    try:
        answer = chat_session.chat(prompt, model, temperature)
        return jsonify({"response": answer})

    except RateLimitError as e:
        logger.warning(f"Rate limit / Quota exhausted: {e}")
        return jsonify(error="Quota esaurita o troppe richieste. Riprova più tardi."), 429

    except OpenAIError as e:
        logger.error(f"Errore API OpenAI: {e}")
        return jsonify(error=f"OpenAI API error: {e}"), 502

    except Exception as e:
        logger.exception("Errore imprevisto")
        return jsonify(error="Errore interno del server"), 500

@app.route("/chat/init", methods=["POST"])
def chat_init():
    data = request.get_json() or {}
    system_messages = data.get("system_messages")
    if not isinstance(system_messages, list) or not system_messages:
        return jsonify({"error": "Il campo 'system_messages' è mancante o non è una lista valida."}), 400

    added = []
    skipped = []
    # Prova ad aggiungere ogni system message solo se non ci sono ancora interazioni
    for msg in system_messages:
        if chat_session.add_initial_system(msg, force=True):
            added.append(msg)
        else:
            skipped.append(msg)

    chat_session.system_message_count += len(added)

    return jsonify({
        "added_system_messages": added,
        "skipped_system_messages": skipped,
        "history_size": len(chat_session.messages)
    }), 200

@app.route("/chat/history", methods=["GET"])
def chat_history():
    """
    Restituisce la cronologia dei messaggi della sessione di chat.
    """
    return jsonify(chat_session.messages), 200

# Endpoint per appendere un messaggio in coda (ultimo)
@app.route("/chat/append", methods=["POST"])
def append_message():
    data = request.get_json() or {}
    role = data.get("role")
    content = data.get("content")
    # Verifica che il ruolo sia valido e il contenuto sia una stringa
    if role not in ("user", "assistant") or not isinstance(content, str):
        return jsonify({"error": "Richiesta non valida: 'role' deve essere 'system', 'user' o 'assistant' e 'content' una stringa."}), 400
    chat_session.put_message(role, content)
    return jsonify({"appended": {"role": role, "content": content}, "history_size": len(chat_session.messages)}), 200

# Endpoint per aggiungere un messaggio in testa (subito dopo il system)
@app.route("/chat/pop/user", methods=["POST"])
def pop_last_user_message():
    popped = chat_session.pop_last_message()
    if popped:
        return jsonify({"popped": popped}), 200
    return jsonify({"error": "Nessun messaggio da rimuovere"}), 400

# Endpoint per rimuovere l'ultimo messaggio assistant
@app.route("/chat/pop/assistant", methods=["POST"])
def pop_last_assistant_message():
    popped = chat_session.pop_last_assistant()
    # Se è stato rimosso un messaggio assistant, lo restituisce
    if popped:
        return jsonify({"popped": popped}), 200
    return jsonify({"error": "Nessun messaggio da rimuovere"}), 400

# Endpoint per l'ultimo messaggio assistant
@app.route("/chat/last/assistant", methods=["POST"])
def get_last_assistant_message():
    last = chat_session.get_last_assistant()
    # lo restituisce
    if last:
        return jsonify({"last": last}), 200
    return jsonify({"error": "Nessun messaggio da assistant"}), 400

# Endpoint per l'ultimo messaggio utente
@app.route("/chat/last/user", methods=["POST"])
def get_last_user_message():
    last = chat_session.get_last_user()
    # lo restituisce
    if last:
        return jsonify({"last": last}), 200
    return jsonify({"error": "Nessun messaggio da user"}), 400

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=True)
