import pandas as pd

def json_to_board(data):
    """
    Converte lo stato della partita (in formato JSON) in un DataFrame 8×8:
    - index = 'a'..'h', columns = 1..8
    - pezzi bianchi in maiuscolo, neri in minuscolo
    Qualsiasi chiave diversa da 'neri' o 'bianchi' viene ignorata.
    """
    files = list('abcdefgh')
    ranks = list(range(1, 9))
    board = pd.DataFrame('', index=files, columns=ranks)
    
    # Mappa tipo_di_pezzo -> simbolo base (minuscolo)
    mapping = {
        'pedoni':   'p',
        'alfieri':  'b',
        'cavalli':  'n',
        'torri':    'r',
        'regina':   'q',
        're':       'k'
    }
    
    # Iteriamo SOLO sui due colori
    for color in ('neri', 'bianchi'):
        pieces = data.get(color, {})
        if not isinstance(pieces, dict):
            continue
        for ptype, squares in pieces.items():
            symbol = mapping.get(ptype)
            if symbol is None:
                continue
            # maiuscolo se bianco
            if color == 'bianchi':
                symbol = symbol.upper()
            for sq in squares:
                file, rank = sq[0], int(sq[1])
                board.at[file, rank] = symbol

    return board

def board_to_json(board: pd.DataFrame) -> dict:
    """
    Converte un DataFrame 'board' in un dizionario JSON con la struttura:
    {
      "neri": { "pedoni": [...], "alfieri": [...], ... },
      "bianchi": { ... }
    }
    board: DataFrame con index files 'a'-'h' e colonne 1-8 contenente:
           '' per casella vuota, 'P','N','B','R','Q','K' per pezzi bianchi,
           'p','n','b','r','q','k' per pezzi neri.
    """
    # Prepara la struttura vuota
    output = {
        "neri":   {ptype: [] for ptype in ["pedoni","alfieri","cavalli","torri","regina","re"]},
        "bianchi":{ptype: [] for ptype in ["pedoni","alfieri","cavalli","torri","regina","re"]}
    }
    # Mappa simbolo -> tipo di pezzo
    symbol_to_ptype = {
        'p': 'pedoni', 'n': 'cavalli', 'b': 'alfieri',
        'r': 'torri',  'q': 'regina',  'k': 're'
    }

    for file in board.index:       # 'a' … 'h'
        for rank in board.columns: # 1 … 8
            piece = board.at[file, rank]
            if piece == '':
                continue
            color = 'bianchi' if piece.isupper() else 'neri'
            ptype = symbol_to_ptype[piece.lower()]
            square = f"{file}{rank}"
            output[color][ptype].append(square)

    return output

def is_path_clear(board, from_sq, to_sq):
    files = 'abcdefgh'
    ranks = '12345678'
    fx, fy = files.index(from_sq[0]), int(from_sq[1])
    tx, ty = files.index(to_sq[0]), int(to_sq[1])
    dx = (tx - fx) and ((tx - fx)//abs(tx - fx))
    dy = (ty - fy) and ((ty - fy)//abs(ty - fy))
    x, y = fx + dx, fy + dy
    while (x, y) != (tx, ty):
        if board.at[files[x], y] != '':
            return False
        x += dx; y += dy
    return True

def is_legal_move(piece, from_sq, to_sq, board, player_color):
    """
    Verifica se la mossa è legale sia dal punto di vista del movimento 
    del pezzo sia del colore del giocatore.

    - piece: codice del pezzo (maiuscolo=bianco, minuscolo=nero)
    - from_sq, to_sq: stringhe come 'e2', 'e4'
    - board: pandas DataFrame
    - player_color: 'white' o 'black'
    """
    if piece is None:
        file_from, rank_from = from_sq[0], int(from_sq[1])
        piece = board.at[file_from, rank_from]
        if not piece:
            raise ValueError(f"Origin cell {from_sq} is empty: no piece to move.")

    # 1) controllo colore
    if player_color.lower() == 'white' and piece.islower():
        return False
    if player_color.lower() == 'black' and piece.isupper():
        return False

    files = 'abcdefgh'
    fx, fy = files.index(from_sq[0]), int(from_sq[1])
    tx, ty = files.index(to_sq[0]), int(to_sq[1])
    dx, dy = tx - fx, ty - fy
    p = piece.lower()

    # Cavallo
    if p == 'n':
        return (abs(dx), abs(dy)) in [(1,2),(2,1)]
    # Re
    if p == 'k':
        return max(abs(dx), abs(dy)) == 1
    # Pedone
    if p == 'p':
        direction = 1 if piece.isupper() else -1
        dest_empty = (board.at[to_sq[0], ty] == '')
        # mossa in avanti di 1
        if dx == 0 and dy == direction and dest_empty:
            return True
        # mossa doppia da casa
        start_rank = 2 if piece.isupper() else 7
        if dx == 0 and fy == start_rank and dy == 2*direction and dest_empty:
            mid_rank = fy + direction
            if board.at[from_sq[0], mid_rank] == '':
                return True
        # cattura diagonale
        if abs(dx) == 1 and dy == direction:
            target = board.at[to_sq[0], ty]
            if target != '' and (target.isupper() != piece.isupper()):
                return True
        return False
    # Torre, alfiere, regina
    if p in ('r','b','q'):
        if p == 'r' and not (dx == 0 or dy == 0): return False
        if p == 'b' and abs(dx) != abs(dy):      return False
        if p == 'q' and not (dx == 0 or dy == 0 or abs(dx)==abs(dy)): return False
        return is_path_clear(board, from_sq, to_sq)

    # Tutti gli altri casi non gestiti
    return False

def boards_equal(board1: pd.DataFrame, board2: pd.DataFrame) -> bool:
    """
    Verifica se due stati di scacchiera (pandas DataFrame) sono identici.
    Restituisce True se tutti i valori di board1 e board2 coincidono nelle stesse posizioni, altrimenti False.
    """
    # Controlla dimensioni e indici
    if board1.shape != board2.shape:
        return False
    if list(board1.index) != list(board2.index) or list(board1.columns) != list(board2.columns):
        return False
    # Confronto elemento per elemento
    return (board1.values == board2.values).all()

def apply_move(piece_code: str, from_sq: str, to_sq: str, board_prev: pd.DataFrame) -> pd.DataFrame:
    """
    Applica una mossa su una board rappresentata come pandas DataFrame,
    spostando il pezzo da `from_sq` a `to_sq` e restituendo la nuova board.

    Parametri:
    - board_prev: pandas DataFrame con indici 'a'-'h' e colonne 1-8.
    - from_sq: stringa casella di partenza, es. 'e2'.
    - to_sq: stringa casella di destinazione, es. 'e4'.
    - piece_code: codice del pezzo da muovere, es. 'P' o 'p'.

    Ritorna:
    - board_next: nuova pandas DataFrame con la mossa applicata.
    """
    # Copia lo stato precedente
    board_next = board_prev.copy()
    # Estrai file e rank di partenza
    file_from, rank_from = from_sq[0], int(from_sq[1])
    # Rimuovi il pezzo dalla casella di partenza

    if piece_code is None:
        piece_code = board_prev.at[file_from, rank_from]
        if not piece_code:
            raise ValueError(f"Origin cell {from_sq} is empty: no piece to move.")

    board_next.at[file_from, rank_from] = ''
    # Estrai file e rank di destinazione
    file_to, rank_to = to_sq[0], int(to_sq[1])
    # Posiziona il pezzo nella destinazione
    board_next.at[file_to, rank_to] = piece_code
    return board_next

def detect_move(prev_board: pd.DataFrame, curr_board: pd.DataFrame):
    """
    Determines which single piece moved between prev_board and curr_board DataFrames.
    Each DataFrame has files 'a'-'h' as index and ranks 1-8 as columns with piece codes or ''.
    Returns (piece, from_sq, to_sq) or raises ValueError.
    """
    removed = []
    added = []
    
    for file in prev_board.index:
        for rank in prev_board.columns:
            prev_piece = prev_board.at[file, rank]
            curr_piece = curr_board.at[file, rank]
            
            if prev_piece != '' and curr_piece == '':
                removed.append(f"{file}{rank}")
            if prev_piece == '' and curr_piece != '':
                added.append(f"{file}{rank}")

    if len(removed) == 0 and len(added) == 0 : 
        raise ValueError(f"Illegal move, expected exactly one piece moved.")     
    
    if len(removed) != 1 or len(added) != 1:
        raise ValueError(f"Illegal move, found removed={removed}, but added={added}.")
    
    from_sq = removed[0]
    to_sq = added[0]
    piece = prev_board.at[from_sq[0], int(from_sq[1])]
    
    if curr_board.at[to_sq[0], int(to_sq[1])] != piece:
        raise ValueError(f"Piece mismatch: expected {piece} at {to_sq}, found {curr_board.at[to_sq[0], int(to_sq[1])]}.")
    
    return piece, from_sq, to_sq

def find_checkers(board, player_color='white'):
    """
    Data una pandas DataFrame 'board' (files 'a'-'h', colonne 1-8),
    restituisce una lista di dict {'from': square, 'piece': code}
    per ogni pezzo avversario che attacca il re di player_color.

    Accetta player_color in inglese ('white','black') o italiano ('bianchi','neri').
    """
    # --- 1) Normalizza il colore e identifica simboli ---
    pc = player_color.lower()
    if pc in ('white', 'bianco', 'bianchi'):
        king_symbol = 'K'; attacker_is_lower = True; opponent_color = 'black'
    elif pc in ('black', 'nero', 'neri'):
        king_symbol = 'k'; attacker_is_lower = False; opponent_color = 'white'
    else:
        raise ValueError(f"Colore non valido: {player_color!r}. Usa 'white/black' o 'bianchi/neri'.")

    # --- 2) Trova il re sul board ---
    king_sq = None
    for file in board.index:
        for rank in board.columns:
            if board.at[file, rank] == king_symbol:
                king_sq = (file, rank)
                break
        if king_sq:
            break
    if not king_sq:
        raise ValueError(f"Re {player_color} non trovato sulla scacchiera.")

    kf, kr = king_sq
    checkers = []

    # --- 3)  Minacce da pedoni ---
    # direzioni di cattura del pedone avversario
    pawn_dirs = [(-1, 1), (1, 1)] if attacker_is_lower else [(-1, -1), (1, -1)]
    for dx, dy in pawn_dirs:
        xf = 'abcdefgh'.find(kf) + dx
        yr = kr + dy
        if 0 <= xf < 8 and 1 <= yr <= 8:
            sq = f"{'abcdefgh'[xf]}{yr}"
            p = board.at[sq[0], yr]
            if p and (p.islower() == attacker_is_lower) and p.lower() == 'p':
                checkers.append({'from': sq, 'piece': p})

    # --- 4) Minacce da cavallo ---
    knight_offsets = [(1,2),(2,1),(-1,2),(-2,1),(1,-2),(2,-1),(-1,-2),(-2,-1)]
    for dx, dy in knight_offsets:
        xf = 'abcdefgh'.find(kf) + dx
        yr = kr + dy
        if 0 <= xf < 8 and 1 <= yr <= 8:
            sq = f"{'abcdefgh'[xf]}{yr}"
            p = board.at[sq[0], yr]
            if p and (p.islower() == attacker_is_lower) and p.lower() == 'n':
                checkers.append({'from': sq, 'piece': p})

    # --- 5) Scansioni ortogonali e diagonali per torri/alfieri/regine e re ---
    directions = {
        'rook':   [(1,0),(-1,0),(0,1),(0,-1)],
        'bishop': [(1,1),(1,-1),(-1,1),(-1,-1)],
    }
    for kind, dirs in directions.items():
        for dx, dy in dirs:
            xf = 'abcdefgh'.find(kf) + dx
            yr = kr + dy
            while 0 <= xf < 8 and 1 <= yr <= 8:
                sq = f"{'abcdefgh'[xf]}{yr}"
                p = board.at[sq[0], yr]
                if p:
                    # è avversario?
                    if p.islower() == attacker_is_lower:
                        low = p.lower()
                        # se è torre/regina in ortogonale, o alfiere/regina in diagonale
                        if (kind=='rook'   and low in ('r','q')) or \
                           (kind=='bishop' and low in ('b','q')):
                            checkers.append({'from': sq, 'piece': p})
                        # re avversario: minaccia sul passo singolo
                        if (abs(dx)==1 or abs(dy)==1) and low=='k':
                            checkers.append({'from': sq, 'piece': p})
                    break
                xf += dx; yr += dy

    return checkers

def is_game_active(board) -> bool:
    """
    Verifica se entrambi i re (bianco 'K' e nero 'k') sono ancora presenti nel board.
    Il board è un pandas DataFrame con indici 'a'-'h' e colonne 1-8 contenenti codici pezzi.
    Restituisce True se il gioco può continuare (entrambi i re presenti), False altrimenti.
    """
    # Estrai i valori del board
    try:
        pieces = board.values.flatten()
    except Exception:
        raise ValueError("Board is not a DataFrame.")
    has_white_king = 'K' in pieces
    has_black_king = 'k' in pieces
    return has_white_king and has_black_king

def game_result(board) -> str:
    """
    Restituisce una stringa con l'esito della partita:
      - se manca il re bianco: 'Partita terminata: Neri vincono!'
      - se manca il re nero: 'Partita terminata: Bianchi vincono!'
      - altrimenti: 'Partita in corso'
    """
    has_white = 'K' in board.values.flatten()
    has_black = 'k' in board.values.flatten()

    if not has_white:
        return "Game over: Black wins!"
    if not has_black:
        return "Game over: White wins!"
    return "Game in progress"