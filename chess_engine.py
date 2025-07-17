import sys
import os
import json
import requests
import uuid
import random
import time
from datetime import datetime, timedelta
from modules.version import VERSION
from modules.chess_core import json_to_board, board_to_json, is_legal_move, apply_move, boards_equal, detect_move, find_checkers, is_game_active, game_result
from utils.app_utils import load_config 
from utils.file_utils import save_content_in_file
from utils.constants import OUT_FOLDER_PARAMETER, DEFAULT_CONFIG_FILE

# TODO porta questo in un file di configurazione config.json
DEFAULT_MODEL = "gpt-4.1-nano"  # Modello predefinito se non specificato

# Mappa dei modelli con i loro ID
model_map: dict[int, str] = {
    0: "gpt-4.1-nano", # 0.10
    1: "gpt-4o-mini",  # 0.15
    2: "gpt-4.1-mini", # $0.40
    3: "o1-mini",      # $1.10
    4: "o4-mini",     # $1.10
    5: "o3-mini",     # $1.10
    6: "gpt-4.1",   #$2.00
    7: "o3",        #$2.00
    8: "gpt-4o"    #$2.50
}

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

def show_board(board):
    """
    Stampa la board con sfondo alternato e pezzi bianchi/neri colorati distintamente:
    - Pezzi bianchi (maiuscoli) in bright white (97)
    - Pezzi neri (minuscoli) in bright black (90)
    """
    files = 'abcdefgh'
    light_bg = '47'   # bianco
    dark_bg  = '100'  # grigio scuro
    reset    = '\033[0m'
    fg_white = '97'   # bright white
    fg_black = '30'   # bright black
    fg_empty = '39'   # default

    print("\n")
    for rank in range(8, 0, -1):
        row = f"{rank} "
        for i, file in enumerate(files):
            piece = board.at[file, rank] or ' '
            bg = light_bg if (i + rank) % 2 == 0 else dark_bg

            if piece.isupper():      # pezzo bianco
                fg = fg_white
            elif piece.islower():    # pezzo nero
                fg = fg_black
            else:                    # vuoto
                fg = fg_empty

            cell = f"\033[{fg};{bg}m {piece} {reset}"
            row += cell
        print(row)
    footer = "   " + "".join(f" {f} " for f in files)
    print(footer)
    print("\n")

# Inizializza una sessione di ChatGPT con regole specifiche per il gioco degli scacchi
# Questa funzione prepara le regole e gli obiettivi per il modello, in modo che possa rispondere in modo pertinente alle mosse degli avversari.
def init_chatgpt_session(board_state, language='italiano'):
    rules = f"""
    Regole:
    - La lingua dei messaggi di gioco deve essere in {language}.
    - La lingua dei messaggi di errore o di avvertimento sarà in inglese, tra parentesi quadre []: sono indicazioni che ti aiuteranno a migliorare il gioco.
    - Sei un esperto di gioco di scacchi, devi analizzare la seguente situazione di gioco, rappresentata da una codifica in formato JSON che mostra lo stato dell'organizzazione dei pezzi neri e bianchi sulla scacchiera. 
    {json.dumps(board_state, indent=4)}
    - Tu giochi dalla parte dei Neri e devi rispondere alla mossa proposta dai Bianchi che verrà comunicata in ogni messaggio (nel formato "origine-destinazione") insieme alla stato completo della scacchiera in JSON. 
    - La partita è finita quando uno delle due liste di Re è vuota.
    """

    target = f"""
    Obiettivi:
    - Analizza la mossa proposta dai Bianchi e agisci in risposta. Difendi il Re Nero se è sotto scacco.
    - Individua e proponi la mossa più efficace per contrastare il gioco dei Bianchi, rispettando le regole e la situazione del gioco.
    """
    
    output = f"""
    Output: Restituisci esclusivamente un oggetto JSON con:
    - Una chiave "mossa_proposta" dai Neri contenente la stringa "origine-destinazione" (per esempio "e7-e6").
    - Tutte le liste “bianchi” e “neri” aggiornate secondo la "mossa proposta" dai Neri. 
    - una chiave opzionale denominata "commento_giocatore" contenente suggerimenti, citazioni a tecniche o passaggi storici in relazione alla "mossa_proposta"
    - una chiave opzionale denominata "messaggio_avversario" contenente un messaggio di sfida che non riveli però la strategia relativa alla "mossa_proposta"
    """

    # 1. Prepara i messaggi di sistema che vuoi iniettare
    system_messages = [
        rules,
        target,
        output
        ] 

    # 2. Chiama l’endpoint /chat/init
    resp = requests.post(
        "http://localhost:5000/chat/init",
        json={"system_messages": system_messages},
        headers={"Content-Type": "application/json"}
    )
    print("Let's start ChatGPT Session...")
    # 3. Controlla l’esito
    if resp.status_code == 200:
        result = resp.json()
        print("System messages added:", result["added_system_messages"])
        print("System messages skipped:", result["skipped_system_messages"])
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

def send_message_to_proxy_service(role="user", content = ""):

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
        print(f"❌ Error {resp.status_code}:", resp.text)

def send_chess_move_to_chatgpt(board_state, proposed_action, model: str = DEFAULT_MODEL,
             temperature: float = 0.5, language='italiano'):
    prompt_text = f"""
    Input: Fornisco lo stato corrente della scacchiera in formato JSON.
    {json.dumps(board_state, indent=4)}
    Mossa proposta dai Bianchi: {proposed_action}
    """
    
    # 3. Prepara il payload JSON
    payload = {
        "prompt": prompt_text,
        "model": model,
        "temperature": temperature
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
        # print(f"[DEBUG] ChatGPT error response: {response_data}")
        return None
                           
def repair_json_board(json_board):
    
    raw = json_board.strip()

    # 1) Rimuovi eventuali code fences
    if raw.startswith("```"):
        # rimuove tutti i backtick e la parola json
        raw = raw.strip("`").replace("json", "", 1).strip()

    # 2) Controlla quante graffe mancano e aggiungile
    open_braces  = raw.count("{")
    close_braces = raw.count("}")
    if open_braces > close_braces:
        raw += "}" * (open_braces - close_braces)

    # 3) Tenta il parsing
    try:
        data = json.loads(raw)
    except Exception as e:
        print("Malformed JSON:", e)
        # qui puoi loggare `raw` per debug
        raise

    return json.dumps(data, indent=4, ensure_ascii=False)

def warn_if_in_check(board, color, detect_ai_move = None):
    """
    Controlla se il re bianco è sotto scacco: se sì stampa un avviso con i pezzi che lo attaccano.
    """
    warn_message = None

    try:
        checkers = find_checkers(board, color) # Trova i pezzi che attaccano il re del colore specificato
        if len(checkers) > 0 and detect_ai_move is not None: 
            piece, from_sq, to_sq = detect_ai_move[0], detect_ai_move[1], detect_ai_move[2]
            if is_legal_move(piece, from_sq, to_sq, board, color):
                check_board = apply_move(piece, from_sq, to_sq, board)
                checkers_l2 = find_checkers(check_board, color)
                if not checkers_l2:
                    checkers = []  # Se la mossa proposta non lascia il re in scacco, resetta i checkers
    except ValueError as e:
        print(f"Error: {e}")
        warn_message = f"Error: {e}"

    if checkers:
        attackers = ", ".join(f"{c['piece']} da {c['from']}" for c in checkers)
        warn_message = (f"{color.capitalize()} king is under attack: {attackers}")

    return warn_message

def play_match(config, json_board, execution_id, is_human_turn):

    print(f"Game start! - Version n. {VERSION}")

    # TODO: utilizzare config per parametri come modello, temperatura, ecc.
    # print(f"Configurazione partita: {config}")
    CURRENT_MODEL = DEFAULT_MODEL  # Modello attualmente in uso
    START_TIME = datetime.now()
    TIME_LIMIT = timedelta(minutes=30)
    RETRY_TIME = 3
    retry_count = 0
    max_retries = 2
    piece_code = '' 
    from_sq = ''
    to_sq = ''
    initial_board = json.loads(json_board)
    board_prev = json_to_board(initial_board)

    is_human_turn = True  # flag per il turno umano

    init_chatgpt_session(json_board, language='italiano')

    while is_game_active(board_prev) and not time_exceeded(START_TIME, TIME_LIMIT):
        # mostra_board(board_prev)
        show_board(board_prev)

        if is_human_turn:
            # Aspetta input da tastiera
            # Formato atteso: "<piece> <from_sq> <to_sq>", es. "P a2 a3"
            user_input = input("Enter move (eg. P a2 a3): ").strip().split()
            if len(user_input) != 3:
                print("Invalid input, use: <piece> <origin> <destination>")
                continue

            piece_code, from_sq, to_sq = user_input
            # Verifica che il pezzo esista davvero in from_sq
            file_from, rank_from = from_sq[0], int(from_sq[1])
            if board_prev.at[file_from, rank_from] != piece_code:
                print(f"No piece '{piece_code}' at {from_sq}")
                continue

            # Verifica legalità mossa
            if not is_legal_move(piece_code, from_sq, to_sq, board_prev, "white"):
                print(f"Move {piece_code} {from_sq}->{to_sq} is not valid")
                continue

            # Applica la mossa: crea board_next da board_prev
            board_next = apply_move(piece_code, from_sq, to_sq, board_prev)

            # Verifica se il re bianco è sotto scacco dopo la mossa
            warn_checkers = warn_if_in_check(board_next, "white")
            if warn_checkers is not None:
                send_message_to_proxy_service(role="user", content=f"[{warn_checkers}]")
                print(warn_checkers)
                continue 

            # Aggiorna lo stato
            board_prev = board_next
            is_human_turn = False  # passa il turno all'avversario (o al motore)

            print(f"Move executed: {piece_code} {from_sq}->{to_sq}")
            # (Here you could serialize board_prev or call the opponent engine)
        else:
            # Logica per mossa del computer...
            retry_count = 0
            computer_response = None

            detect_ai_move = None
            while computer_response is None and retry_count < max_retries:
                retry_count += 1
                temperature = random.uniform(0.70, 0.95)  # Imposta una temperatura casuale tra 0.70 e 0.95
                computer_response = send_chess_move_to_chatgpt(board_to_json(board_prev), f"{from_sq}-{to_sq}", model=CURRENT_MODEL, temperature=temperature)

                if computer_response is None:
                    print("[DEBUG] No response from ChatGPT. Retrying...")
                    time.sleep(RETRY_TIME)
                    continue

                save_content_in_file(computer_response, "resources/responses", f"chat-{execution_id}")

                # Prova a riparare il JSON se necessari
                try:
                    computer_response = repair_json_board(computer_response)    
                except Exception as e:
                    print(f"Error repairing JSON: {e}")
                    # Rimuove l'ultimo messaggio assistant visto che JSON non è valido
                    remove_last_assistant_message()
                    repair_feedback_message = f"The board you sent seems incorrect as JSON, please use this representation and try again to rework a correct move: {board_to_json(board_prev)}"
                    send_message_to_proxy_service(role="user", content=f"[{repair_feedback_message}]")
                    computer_response = None
                    continue

                # Trasforomo la risposta di chatgpt nell'ipotetico stato futuro della scacchiera
                board = json.loads(computer_response)
                board_next = json_to_board(board)

                try:
                    # Verifica se è presente una mossa per differenza tra stato originale e futuro 
                    detect_ai_move = detect_move(board_prev, board_next)
                    print(f"[DEBUG] Relevated move from engine: {detect_ai_move}")
                    computer_play_correct = is_legal_move(detect_ai_move[0], detect_ai_move[1], detect_ai_move[2], board_prev, "black")
                    
                    # verifico se la mossa  NON è valida ed in caso do un feedback a chatgpt
                    if not computer_play_correct:
                        remove_last_assistant_message()
                        move_feedback_message = (f"Illegal move proposed by assistant: '{detect_ai_move[1]}->{detect_ai_move[2]}' at this point is not valid for Black.")
                        print(f"[DEBUG] {move_feedback_message}")
                        send_message_to_proxy_service(role="user", content=f"[{move_feedback_message}]")
                        computer_response = None
                except Exception as e1:
                    # forse chatgpt ha giocato correttamente, ma non ha aggiornato lo stato della scacchiera, in questo caso devo insegnargli come fare
                    print(f"[DEBUG] Error during move detection: {e1}")
                    board_feedback_message = "" # str(e1)
                    message_removed = get_last_assistant_message()
                    payload = {}
                    try:
                        payload = json.loads(message_removed['content'])
                    except json.JSONDecodeError as e2:
                        # qui puoi loggare l’errore e decidere un fallback
                        print("Malformed JSON:", e2)
                    move = payload.get('mossa_proposta', None)
                    # ad una prima analisi la differenza tra lo stato della scacchiera successivamente alla mossa proposta da assistant non sembra corretta
                    if move is not None:
                        board_feedback_message += f" Assistant (Black) propose the move: '{move}', but something seems not coherent with the board definition."
                        if boards_equal(board_prev, board_next):
                            # se sono uguali probabilmente assistant non ha aggiornato la board_next, facciamolo noi e istruiamolo       
                            if move is not None and '-' in move:
                                try:
                                    move = move.replace("x", "-").strip() # rimuovo eventuali x che non sono necessarie
                                    from_sq, to_sq = move.split('-')
                                    if is_legal_move(None, from_sq, to_sq, board_prev, "black"):
                                        # applichiamo la mossa proposta da assistant
                                        correct_board_next = board_to_json(apply_move(None, from_sq, to_sq, board_prev))
                                        print(f"[DEBUG] Board updated with move: {move}")
                                        board_feedback_message += f" Error: the board state has not changed after the move '{move}', update the board in this way: {correct_board_next}"
                                except Exception as e3:
                                    print(f"[ERROR] Failed to apply move: {e3}")
                                    board_feedback_message += f" Error: failed to apply the move '{move}' on the board, please ensure you update the board correctly."
                    else:
                         board_feedback_message += f"Assistant (Black) did not propose a valid move, please provide a valid move for the actual board state: {board_to_json(board_prev)}"
                    send_message_to_proxy_service(role="user", content=f"[{board_feedback_message}]")
                    computer_response = None
                    continue
                
                if computer_response is not None:
                    warn_checkers = warn_if_in_check(board_next, "black", detect_ai_move)
                    if warn_checkers is not None:
                        print(f"[DEBUG] {warn_checkers}")
                        check_feedback_message = f"{warn_checkers} - Please ensure the move does not leave the Black king in check in the actual board state: {board_to_json(board_next)} "
                        send_message_to_proxy_service(role="user", content=f"[{check_feedback_message}]")
                        computer_response = None
                        continue

                    print(f"[DEBUG] Response from ChatGpt: {json.loads(computer_response).get('commento_giocatore', '{}')}")
                    if retry_count > 2:
                        send_message_to_proxy_service(role="user", content=f"[CONGRATULATIONS! Assistant (Black) played last move with success.]")
            
            if detect_ai_move is not None and computer_response is not None:
                board_prev = board_next
                is_human_turn = True
                print(f"Correct Move detected: {detect_ai_move[0]} {detect_ai_move[1]}->{detect_ai_move[2]}")
            else:
                gear_up = get_model_gear(CURRENT_MODEL)+1
                CURRENT_MODEL = model_map.get(gear_up, DEFAULT_MODEL)
                print(f"[DEBUG] Engine cannot retrieve a correct move from ChatGPT, trying to increase model gear to: {CURRENT_MODEL}")
                continue
                
    return game_result(board_prev)

def main():
    params = validate_params()

    if len(params) >= 1 and ('-config' in [param.lower() for param in params]):
        config = load_config(params[1])
    else: 
        config = load_config()
    
    # TODO imposta un parametro per la cartella di output
    output_folder =  os.getcwd() + config.get("folders", {}).get(OUT_FOLDER_PARAMETER, "/out/")
    execution_id = str( uuid.uuid4())
    print(f"Execution ID: {execution_id}")

    is_human_turn = True

    # TODO sposta nel file di configurazione
    json_board = '''
    {
        "neri": {
            "pedoni":   ["a7","b7","c7","d7","e7","f7","g7","h7"],
            "alfieri":  ["c8","f8"],
            "cavalli":  ["b8","g8"],
            "torri":    ["a8","h8"],
            "regina":   ["d8"],
            "re":       ["e8"]
        },
        "bianchi": {
            "pedoni":   ["a2","b2","c2","d2","e2","f2","g2","h2"],
            "alfieri":  ["c1","f1"],
            "cavalli":  ["b1","g1"],
            "torri":    ["a1","h1"],
            "regina":   ["d1"],
            "re":       ["e1"]
        }
    }
    '''

    match_outcome = play_match(
        config=config,
        json_board=json_board,
        execution_id=execution_id,
        is_human_turn=is_human_turn
    )

    send_message_to_proxy_service(role="user", content=f"[{match_outcome}]")
    print(f"[DEBUG] Match status: {match_outcome}")



if __name__ == "__main__":
    main()
