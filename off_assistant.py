import sys
import os
import json
import re
import requests
import uuid
import random
import time
import unicodedata
from collections import deque
from datetime import datetime, timedelta
from modules.version import VERSION
from utils.app_utils import load_config 
from utils.file_utils import save_content_in_file
from utils.constants import OUT_FOLDER_PARAMETER, DEFAULT_CONFIG_FILE
from off_catalog import fetch_product_detail, load_categories, search_category, list_products_for_category, SEARCH_URL, PRODUCT_URL

# TODO porta questo in un file di configurazione config.json
DEFAULT_MODEL = "gpt-4.1-nano"  # Modello predefinito se non specificato

# Mappa dei modelli con i loro ID
model_map: dict[int, str] = {
    0: "gpt-4o-mini",  # 0.15
    1: "gpt-4o",    #$2.50
    2: "gpt-4.1-nano", # 0.10
    3: "gpt-4.1-mini", # $0.40
    4: "o4-mini",     # $1.10
    5: "gpt-4.1"   #$2.00
}

STATE_TEMPERATURES = {
    "search": (0.84, 0.96) ,  # es. per ricerca prodotti
    "product_check": (0.40, 0.50),   # es. per verificare ingredienti/allergeni
    "info": (0.40, 0.50),   # es. per informazioni generali
    "purchase": (0.5, 0.65),
    "compare": (0.45, 0.55),
    "other": (0.45, 0.50),
   # "clarify": (0.5, 0.8),   # es. per disambiguazioni
   # "confirm": (0.2, 0.4),   # es. prima di completare
}

#Determina e modula la temperatura in base allo stato
def get_temperature_for_state(state):
    min_temp, max_temp = STATE_TEMPERATURES.get(state, (0.40, 0.50))
    return round(random.uniform(min_temp, max_temp), 2)

# Data il nome del modello, ritorna il suo indice nella mappa, serve a cambiare modello in caso di errori
def get_model_gear(name: str) -> int:
    """
    Ritorna l'indice del modello dato il suo nome,
    oppure 0 se name è None o non si trova in inv_model_map.
    """
    if not name:
        return 0
    for idx, model in model_map.items():
        if model == name:
            return idx
    return 0
#
def normalize(text):
    return unicodedata.normalize("NFKC", text.strip().casefold())
    
def is_in_list_normalized(target, string_list):
    """
    Verifica se 'target' è contenuto nella lista 'string_list' usando confronti normalizzati.
    
    Args:
        target (str): stringa da cercare
        string_list (List[str]): lista di stringhe in cui cercare

    Returns:
        bool: True se presente, False altrimenti
    """
    target_norm = normalize(target or "")
    return any(normalize(item or "") == target_norm for item in string_list)
# 
def validate_params():
    """
    Verifica i parametri di input dalla riga di comando.
    - Nessun parametro: OK
    - Almeno un parametro: Il primo è obbligatorio, il resto è opzionale.
    """
    if len(sys.argv) == 1:
        # Nessun parametro fornito
        return []

    params = []
    for arg in sys.argv[1:]:
        if arg:
            params.append(arg)

    if len(params) < 1:
        print("Usage: python <this_script_name.py> <param_type> [<params_value> ...]")
        sys.exit(1)

    return params

# TODO necessario utilizzare questo metodo per caricare il file di configurazione
def load_config(filename = DEFAULT_CONFIG_FILE):
    """
    Carica la configurazione dal file JSON specificato.
    Verifica che il file esista prima di tentare di aprirlo.
    
    Parameters:
    filename (str): Il nome del file di configurazione.

    Returns:
    Il contenuto del file di configurazione come dizionario.
    """
    # Verifica se il file esiste nella directory attuale
    if not os.path.exists(filename):
        raise FileNotFoundError(f"The configuration file '{filename}' does not exist.")

    # Leggi il file JSON
    with open(filename, 'r') as file:
        config = json.load(file)

    return config

# Controlla se il tempo limite per la chat è stato superato
def time_exceeded(start_time: datetime, time_limit) -> bool:
    """
    Restituisce True se il tempo corrente ha superato 'start_time' di più di 'time_limit'.

    Parametri:
    - start_time: datetime di inizio partita.
    - time_limit: durata massima consentita, può essere int (minuti) o timedelta.

    Ritorna:
    - True se la differenza tra now e start_time supera time_limit, altrimenti False.
    """
    # Se time_limit è numero, interpretalo come minuti
    if isinstance(time_limit, (int, float)):
        limit_delta = timedelta(minutes=time_limit)
    elif isinstance(time_limit, timedelta):
        limit_delta = time_limit
    else:
        raise ValueError("time_limit must be integer or timedelta.")

    return datetime.now() - start_time > limit_delta

# Inizializza una sessione di ChatGPT con regole specifiche per il gioco degli scacchi
# Questa funzione prepara le regole e gli obiettivi per il modello, in modo che possa rispondere in modo pertinente alle mosse degli avversari.
def init_chatgpt_session(rules, target, output, language='italiano'):
   
    # 1. Prepara i messaggi di sistema che vuoi iniettare
    system_messages = [
        rules,
        target,
        output
        ] 

    # 2. Chiama l’endpoint /chat/init
    resp = requests.post(
        "http://localhost:5000/chat/init",
        json={"system_messages": system_messages, "language": language},
        headers={"Content-Type": "application/json"}
    )
    print("Let's start ChatGPT Session...")
    # 3. Controlla l’esito
    if resp.status_code == 200:
        result = resp.json()
        # print("[DEBUG] System messages added:", result["added_system_messages"])
        # print("[DEBUG] System messages skipped:", result["skipped_system_messages"])
    else:
        print(f"Errore {resp.status_code}: {resp.text}")

def get_last_assistant_message():
    """
    Rimuove l’ultimo messaggio (sia user che assistant): 
    se vuoi solo assistant, potresti poi controllare il role di ritorno.
    """
    resp = requests.post(f"http://localhost:5000/chat/last/assistant")
    if resp.ok:
        last = resp.json()["last"]
        # print("[DEBUG] ✅ Last message:", last)
        return last
    else:
        print(f"❌ Error {resp.status_code}:", resp.text)
        return None

def get_last_user_message():
    """
    Rimuove l’ultimo messaggio (sia user che assistant): 
    se vuoi solo assistant, potresti poi controllare il role di ritorno.
    """
    resp = requests.post(f"http://localhost:5000/chat/last/user")
    if resp.ok:
        last = resp.json()["last"]
        # print("[DEBUG] ✅ Last message:", last)
        return last
    else:
        print(f"❌ Error {resp.status_code}:", resp.text)
        return None

def summarize_messages():
    """
    Rimuove l’ultimo messaggio (sia user che assistant): 
    se vuoi solo assistant, potresti poi controllare il role di ritorno.
    """
    resp = requests.post(f"http://localhost:5000/chat/summarize")
    if resp.ok:
        status = resp.json()["status"]
        print("[DEBUG] ✅ summarize status:", status)
        return status
    else:
        print(f"❌ Error {resp.status_code}:", resp.text)
        return None

def remove_last_assistant_message():
    """
    Rimuove l’ultimo messaggio (sia user che assistant): 
    se vuoi solo assistant, potresti poi controllare il role di ritorno.
    """
    resp = requests.post(f"http://localhost:5000/chat/pop/assistant")
    if resp.ok:
        popped = resp.json()["popped"]
        # print("[DEBUG] ✅ Pop Message:", popped)
        return popped
    else:
        print(f"❌ Error {resp.status_code}:", resp.text)
        return None

def append_message_to_chat(role="user", content = ""):
    # Invia un messaggio alla chat e ritorna la dimensione della sessione della chat
    resp = requests.post(
        f"http://localhost:5000/chat/append",
        json={"role": role, "content": content},
        headers={"Content-Type": "application/json"}
    )
    if resp.ok:
        data = resp.json()
        # print("[DEBUG] ✅ Append Message:", data["appended"])
        # print("[DEBUG] 🔢 History Size:", data["history_size"])
    else:
        print(f"❌[ERROR] {resp.status_code}:", resp.text)

def send_message_to_chat(prompt_text, model: str = DEFAULT_MODEL,
             temperature: float = 0.5, language='italiano'):
    # a differenza di append_message_to_chat, questa funzione invia un messaggio specifico e ritorna la risposta del modello.
    
    # 3. Prepara il payload JSON
    payload = {
        "prompt": prompt_text,
        "model": model,
        "temperature": temperature, 
        "language": language
    }

    # 4. Invia la richiesta al tuo Flask server in ascolto su localhost:5000
    response = requests.post(
        "http://localhost:5000/chat",
        json=payload,
        headers={"Content-Type": "application/json"}
    )

    # 5. Gestisci la risposta
    if response.status_code == 200:
        response_data = response.json()
        # print(f"[DEBUG] ChatGPT response: {response_data}")
        return response_data["response"]
    else:
        response_data = response.json()
        print(f"[DEBUG] ChatGPT error response: {response_data}")
        return None
   
# Carica le categorie dal catalogo OpenFoodFacts: TODO potrebbe essere spostato in un file di utilità
def sanitize_json_string(json_string):
    """
    Tenta di riparare una stringa JSON che contiene virgolette non escapate.
    ATTENZIONE: È una soluzione euristica, non perfetta.
    """
    # Rimuove caratteri di controllo non stampabili
    json_string = re.sub(r"[\x00-\x1F\x7F]", "", json_string)

    # Sostituisce doppie virgolette erronee (es: "... \" ... \"" --> corretti)
    json_string = re.sub(r'(?<!\\)"(?![:,{}\[\]\s])', r'\\"', json_string)

    return json_string

# Main chat loop
def play_match(config, initial_state, execution_id, is_human_turn):

    print(f"Game start! - Version n. {VERSION}")

    # TODO: utilizzare config per parametri come modello, temperatura, ecc.
    # print(f"Configurazione partita: {config}")
    CURRENT_MODEL = DEFAULT_MODEL  # Modello attualmente in uso
    START_TIME = datetime.now()
    TIME_LIMIT = timedelta(minutes=45)
    RETRY_TIME = 3
    retry_count = 0
    max_retries = 2
    is_human_turn = True  # flag per il turno umano
    chatbot_language = 'inglese'
    most_relevant_items_num = 8
    max_products_per_category = 5
    total_max_products = 30

    # Inizializza la sessione di ChatGPT con le regole del gioco
    rules = config.get("rules", f"""\
    - Lingua: i messaggi dell'assistente verso l'utente devono essere in italiano.
    - Formato RISPOSTA: restituisci SEMPRE e SOLO un oggetto JSON (nessun testo fuori dal JSON).
    - Struttura JSON obbligatoria (chiavi fisse): {{
        "request": "",
        "request_type": "",
        "brands": [],
        "products": [],
        "selected_product": "",
        "category": "",
        "result": "",
        "suggestion": "",
        "completed": false
    }}
    - Valori: tutte le proprietà devono contenere STRINGHE in {chatbot_language}.
    "completed" è booleano (true/false).
    - Avvio/chiusura conversazione: quando non ci sono richieste o una richiesta è stata completata,
    rivolgiti come un commesso: "come posso aiutarti?", "in cosa posso esserti utile?",
    "posso aiutarti ancora?" (queste frasi non vanno stampate fuori dal JSON; usa "suggestion").
    - Richiesta utente: sarà racchiusa tra i caratteri '<' e '>' (es.: <buy iphone 13>).
    - I messaggi di tuning del comportamento saranno in {chatbot_language}, tra parentesi quadre [ ... ];
    influenzano il comportamento ma NON vanno mai riportati nell'output JSON.
    - Vietato produrre testo extra, codice, spiegazioni o blocchi markdown al di fuori del JSON.
    - Anche se non specificato direttamente cerca di completare tutti i campi di output JSON. Determina 'category' e 'products' in base alla richiesta dell'utente o identifica i valori più rilevanti dal contesto.
      Le categorie sono parole concatenate da trattini e spesso iniziano il codice lingua seguito dai due punti (es.: "en:soft-drinks", "en:chocolate-bars").
    - Se non riesci a completare la richiesta, imposta 'completed' a 'true'.
    - il numero di elementi in 'products' deve essere limitato a {total_max_products}.
    - Ogni richiesta che non riguarda prodotti alimentari deve essere ignorata e completata con 'completed': true.
    """)

    target = config.get("target", f"""\
    Obiettivo: agire come commesso di negozio virtuale per comprendere l'intento dell'utente,
    classificare la richiesta (es.: purchase, product_check, compare, info), dedurre la categoria di prodotto dalla richiesta,
    ricercare/riassumere prodotti e restituire un JSON conforme. Quando "completed" è 'true',
    proponi una nuova azione/richiesta tramite il campo "suggestion" (in {chatbot_language}) e attendi nuovo input.
    """)

    output = config.get("output", f"""\
    Output atteso (unica riga, nessun testo extra):
    {{"request":"","request_type":"","products":[],"category":"","result":"","suggestion":"","completed":false}}

    Linee guida di valorizzazione:
    - "request": trascrivi la richiesta utente (senza i delimitatori < >) in {chatbot_language}. Campo obbligatorio.
    - "request_type": uno tra "purchase","product_check","compare","info","search","other". Obbligatorio.
        Se "purchase" nella chat il campo "products" deve contenere almeno un prodotto.
        Se "info" allora le informazioni sono da reperire all'interno della chat (non serve cercare prodotti) se la lista dei prodotti è valorizzata con almeno {most_relevant_items_num} elementi, altrimenti bisogno utilizzare "search".
        Se "search" allora l'utente vuole cercare prodotti
        Se "product_check", "compare" allora nella chat deve essere presente il 'products detail' (brand, ingredients, allergens).
        Se "other" allora la richiesta non rientra in nessuna delle precedenti categorie, l'assistente deve proporre in 'suggestion' una nuova richiesta all'utente.
        Se non riesci a classificare la richiesta, usa "other".
    - "brands": elenco dei brand relativi ai prodotti trovati (se disponibili).
    - "products": elenco con nomi dei prodotti in {chatbot_language}.
    - "selected_product": nome del prodotto selezionato esplicitamente dall'utente. Se specificato allora la richiesta deve essre di tipo purchase, product_check o info.
    - "category": categoria prodotto in {chatbot_language} dedotta dalla richiesta utente (es.: "cake","soft-drinks","snacks"). Obbligatorio.
    - "result": esito sintetico della richiesta in {chatbot_language} (max 1-2 frasi). Obbligatorio.
    - "suggestion": prossimo passo utile in {chatbot_language} (es.: "Would you like me to filter by price?"). Obbligatorio.
    - "completed": false finché servono altre informazioni; true quando la richiesta è soddisfatta.
    """)

    rules = rules + "\n" + json.dumps(initial_state, indent=4, ensure_ascii=False)
    init_chatgpt_session(rules, target, output, language='italiano')

    # Variabili di stato
    last_query = ""
    # products_history = []
    products_history = deque(maxlen=total_max_products)  # Mantiene solo gli ultimi 50 prodotti
    # brand_history = []
    brand_history = deque(maxlen=total_max_products)  # Mantiene solo gli ultimi 50 brand
    last_request_type = ""
    current_temperature = 0.5
    selected_product = ""

    while not time_exceeded(START_TIME, TIME_LIMIT):
    
        if is_human_turn:

            user_input = input("User request: ").strip().replace("?", "").split()
            if len(user_input) <= 2:
                print("Invalid input, please provide a complete request.")
                continue

            response = send_message_to_chat(prompt_text=f"<original request:{user_input}>", model=CURRENT_MODEL, temperature=current_temperature)

            if response is None:
                print("[DEBUG] No response from ChatGPT. Retrying...")
                time.sleep(RETRY_TIME)
                continue

            #print(f"[DEBUG] JSON Response from ChatGPT {response}")
            payload = json.loads(response)          # -> dict Python
            query = payload.get('category', '').replace('-', ' ').strip()
            selected_product = (payload.get('selected_product') or '').strip().casefold()

            # TODO: se la categoria non è presente verificare se è possibile recuperare il codice prodotto per cercare direttamente un dettaglio
            
            # Gestione della query e momorizzazione dell'ultima query valida, riumovere categorie con meno di 3 caratteri
            if query and query != last_query:
                last_query = query
            elif not query and last_query:
                query = last_query

            # TODO verificare come evitare di ricaricare la lista prodotti durante la ricerca dei dettagli
            # quando la richiesta è di tipo "info" non serve cercare prodotti ma il chatbot deve rispondere con le informazioni contenute nella chat
            if last_request_type != "info":
                slugs = search_category(query)
                last_request_type = payload.get('request_type', '').strip()
                completed = payload.get('completed', '')

                if completed == True and selected_product:
                    append_message_to_chat(role="user", content=f"[The request is marked as completed. Assistant should confirm the completion and suggest a new request or action to the user.]")
                    is_human_turn = False
                    # TODO non sono sicuro che sia corretto azzerare la storia
                    # brand_history = []
                    # products_history = []
                    continue
                else: 
                    completed = False

                if slugs is None:
                    print(f"[DEBUG] Nessuna categoria trovata (query: {query}).")
                    message= f"No category found for the query: {query}. User have to try again with a different query. Assistant should try to suggest a more specific query or check the spelling."
                    append_message_to_chat(role="user", content=f"[{message}]")
                else:
                    # print(f"[DEBUG] Found category slugs: {slugs}")
                    products = []
                    seen = set()
                    stop_loading = False

                    for slug in slugs:
                        if stop_loading:
                            # print(f"[INFO] max product threshold {total_max_products} reached.")
                            break

                        for p in list_products_for_category(slug, page_size=max_products_per_category):
                            if len(products) >= total_max_products:
                                stop_loading = True
                                break  # esce solo dal ciclo interno

                            code = p.get("code")
                            if code and code not in seen:
                                seen.add(code)
                                products.append(p)

                    # Ordinamento risultati
                    # si potrebbe ordinare per rilevanza, selected_product
                    # il parametro "selected_products" è utilizzato per indicare quali tra i prodotti rilevanti è stato selezionato
                    # il prodotto selezionato deve andare in prima posizione nella lista
                    selected_normalized = normalize(selected_product or "")

                    def norm_name(p):
                        return normalize(p.get("product_name") or "")

                    products.sort(
                        key=lambda p: (
                            0 if selected_normalized and norm_name(p) == selected_normalized else 1,
                            norm_name(p)
                        )
                    )

                    if last_request_type not in ("search", "other") and products:

                        # se c'è un prodotto selezionato provo a ridurre la rosa dei prodotti in base al numero dei retry
                        if selected_product and most_relevant_items_num - retry_count > 1:
                            products = products[:most_relevant_items_num - retry_count] 
                        else:
                            products = products[:most_relevant_items_num]
                    
                    # limita la storia ad un certo numero di elementi, i primi arrivati vanno rimossi
                    for name in (p.get("product_name", "") for p in products if p.get("product_name")):
                        if name not in products_history:
                            products_history.append(name)

                    for brand in (p.get("brands", "") for p in products if p.get("brands")):
                        if brand not in brand_history:
                            brand_history.append(brand)

                    # non ci sono prodotti
                    if not products:
                        message = f"No products found for the category: '{slugs}'. Please try again with a different category."
                        append_message_to_chat(role="user", content=f"[{message}]")
                        # print(f"[DEBUG] No products found for category slugs: {slugs}")
                    else:
                        # ci sono ma sono troppi
                        # print(f"[DEBUG] Found products: {products}")
                        if len(products) > most_relevant_items_num:
                            message = f"Too many products: found {len(products)} for the selected categories, please reduce the number of products updating the JSON field 'products' with the most relevant {most_relevant_items_num - retry_count} items in the products set: {list(products_history)}. Update the JSON 'category' field with the most useful and specific element in the set, related to the selected products: [{', '.join(slugs)}]. Get a related 'result' for the original user request with a concise summary (1-2 sentences). Suggest to the user next steps in the 'suggestion' field to refine the request or get more details about the products found."
                            # filtro caratteri strani prima di inviare il messaggio
                            message = message.replace(', ,', '')
                            append_message_to_chat(role="user", content=f"[{message}]")
                        else:
                            # se il numero dei risultati è accettabile allora procedo a recuperare i dettagli
                            # TODO: verificare se selected_product è in products prima di procedere
                            product_names = [p.get("product_name", "") for p in products]
                            if selected_product and not is_in_list_normalized(selected_product, product_names):
                                message = f"The selected product '{selected_product}' is not in the product list found for the category '{slugs}'. Please try again with a different product or check the spelling. Update the JSON field 'products' with the most relevant items in the product list: [{', '.join(p['product_name'] for p in products if 'product_name' in p)}]. Update the JSON 'category' field with the most useful and specific element in the list: [{', '.join(slugs)}]. "
                                print(f"[DEBUG] {message}")

                            message = f"Found {len(products)} products in category '{slugs}'. Update the JSON field 'result' with information requested by the user. Update the JSON field 'products' with the most relevant items in the product list: [{', '.join(p['product_name'] for p in products if 'product_name' in p)}]. Update the JSON 'category' field with the most useful and specific element in the list: [{', '.join(slugs)}]. "
                            for p in products:
                                detail = fetch_product_detail(p["code"])
                                if not detail:
                                    continue
                                else:
                                    product_name = p.get('product_name')
                                    brand = p.get('brands')

                                    if product_name and brand:
                                        message += (
                                            f"\nFound 'product details' for '{product_name}' with code '{p['code']}': "
                                            f"- Brand '{brand}', "
                                            f"- Ingredients: {detail.get('ingredients', 'N/A')}, "
                                            f"- Allergens: {detail.get('allergens', 'N/A')}. "
                                            )
                            message += (f"Suggest to the user the most relevant product's details (brand, ingredients, allergens).")
                            # filtro caratteri strani prima di inviare il messaggio TODO definire una funzione
                            message = message.replace(', ,', '')
                            append_message_to_chat(role="user", content=f"[{message}]")

            is_human_turn = False  # passa il turno all'assistente
            
        else:
            # Logica per mossa del computer...
            retry_count = 0
            computer_response = None
            computer_result = None
            computer_completed = False

            while computer_response is None and retry_count < max_retries:
                retry_count += 1
                temperature = get_temperature_for_state(last_request_type)
                current_temperature = temperature
                print(f"[DEBUG] temperature {temperature:.2f}")
                # Propone all'LLM una formulazione della risposta
                prompt_text = f"""
                               response to the user request using a json format like that:
                                {{
                                    "request:":"<user request>",
                                    "request_type":"{last_request_type}",
                                    "brands":{list(brand_history)},
                                    "products":{list(products_history)},
                                    "selected_product":"{selected_product}",
                                    "category":"{query}",
                                    "result":"<build result requested by user, using the products found in the product list>",
                                    "suggestion":"<next step suggestion to the user, like 'how can I help you?'>",
                                    "completed":false
                                }}
                               """
                computer_response = send_message_to_chat(prompt_text, model=CURRENT_MODEL, temperature=temperature)

                if computer_response is None:
                    print("[DEBUG] No response from ChatGPT. Retrying...")
                    time.sleep(RETRY_TIME)
                    continue
  
                if computer_response is not None:
                    # TODO il salvataggio della risposta in un file è opzionale, andrebbe storicizzato in un database
                    save_content_in_file(computer_response, "resources/responses", f"chatbot-{execution_id}")

                    try:
                        content = json.loads(computer_response)
                    except json.JSONDecodeError as e:
                        # potrebbe essere necessario riparare il JSON
                        print(f"[WARNING] JSONDecodeError: {e}. trying sanification...")

                        # Prova a riparare il JSON
                        fixed = sanitize_json_string(computer_response)

                        try:
                            content = json.loads(fixed)
                            print("[INFO] JSON repaired successfully.")
                        except json.JSONDecodeError as e2:
                            print(f"[ERROR] fail to repair: {e2}")
                            print(f"[DEBUG] Original response was: {computer_response[:500]}")
                            remove_last_assistant_message()
                            computer_response = None
                            time.sleep(RETRY_TIME)
                            continue

                    # Estrai i campi
                    products = content.get("products", [])
                    result = content.get("result", "")
                    suggestion = content.get("suggestion", "")

                    product_list_str = "\n".join(f"- {p}" for p in products)

                    # Mostra in output la risposta del chatbot
                    print(f"\033[34mResponse from ChatGpt:\n{product_list_str}\n{result}\n{suggestion}\033[0m")

            if retry_count > max_retries:
                # informa l'utente che non si riesce a completare la richiesta
                print(f"[DEBUG] Max retries {max_retries} exceeded.")
                append_message_to_chat(role="user", content=f"[The assistant cannot complete the user requestm, please set the 'completed' param to 'True'.]")
            else:
                append_message_to_chat(role="user", content=f"[CONGRATULATIONS! Assistant proposed a great suggestion.]")
       
            if computer_response is not None:
                is_human_turn = True
                computer_result = {json.loads(computer_response).get('result', '{}')}
                computer_completed = {json.loads(computer_response).get('completed', '{}')}
            else:
                # Se non si riesce ad ottenere una risposta forse il proxy opeaai ha terminato i token disponibili
                # CALL FOR SUMMARIZE MESSAGE
                summarize_messages()

                # Gear up del modello
                gear_up = get_model_gear(CURRENT_MODEL)+1
                CURRENT_MODEL = model_map.get(gear_up, DEFAULT_MODEL)
                print(f"[DEBUG] Engine cannot retrieve a correct response from ChatGPT, trying to increase model gear to: {CURRENT_MODEL}")
                continue
                
    return "Assistant complete with result= {computer_result} and completed= {computer_completed} after {retry_count} retries."

def main():
    params = validate_params()

    if len(params) >= 1 and ('-config' in [param.lower() for param in params]):
        config = load_config(params[1])
    else: 
        config = load_config("/mnt/d/DEV/Prj/TEMP/PromptChess/config.json")
    print(f"[DEBUG] Configuration loaded: {config}")
    # TODO imposta un parametro per la cartella di output
    output_folder =  os.getcwd() + config.get("folders", {}).get(OUT_FOLDER_PARAMETER, "/out/")
    execution_id = str( uuid.uuid4())
    print(f"\nExecution ID: {execution_id}")

    is_human_turn = False

    initial_state = config.get("initial_state", None)

    match_outcome = play_match(
        config=config,
        initial_state=initial_state,
        execution_id=execution_id,
        is_human_turn=is_human_turn
    )

    append_message_to_chat(role="user", content=f"[{match_outcome}]")
    print(f"[DEBUG] Match status: {match_outcome}")

if __name__ == "__main__":
    main()
