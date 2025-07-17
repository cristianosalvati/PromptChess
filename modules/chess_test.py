import json
from chess_core import json_to_board, board_to_json, is_legal_move, detect_move, find_checkers

# Stati di esempio
prev_json = '''
{
  "neri": {
    "pedoni": ["a7","d6","f5","h5"],
    "alfieri": [],
    "cavalli": ["e8"],
    "torri": [],
    "regina": [],
    "re": ["b6"]
  },
  "bianchi": {
    "pedoni": ["a2","b2","h2"],
    "alfieri": [],
    "cavalli": [],
    "torri": [],
    "regina": [],
    "re": ["a4"]
  },
  "mossa_proposta": "a2-a3",
  "commento_giocatore": "Spingere il pedone a3 crea spazio per il re e impedisce infiltrazioni laterali.",
  "messaggio_avversario": "Il tuo re rimane intrappolato, buona fortuna a liberarti!"
}
'''
next_json = '''
{
  "neri": {
    "pedoni": ["a7","d6","f5","h5"],
    "alfieri": [],
    "cavalli": ["e8"],
    "torri": [],
    "regina": [],
    "re": ["b6"]
  },
  "bianchi": {
    "pedoni": ["a2","b3","h2"],
    "alfieri": [],
    "cavalli": [],
    "torri": [],
    "regina": [],
    "re": ["a4"]
  }
}
'''

# Load and build boards
prev_state = json.loads(prev_json)
next_state = json.loads(next_json)
board_prev = json_to_board(prev_state)
board_next = json_to_board(next_state)

detect = detect_move(board_prev, board_next)
print(f"Mossa rilevata: {detect}")

piece   = detect[0]
from_sq = detect[1]
to_sq   = detect[2]

# Test legality
legal = is_legal_move(piece, from_sq, to_sq, board_prev)

print(f"Pezzo mosso: {piece} da {from_sq} a {to_sq}")
print(f"Mossa legale? {'Sì' if legal else 'No'}")

checkers = find_checkers(board_prev)
print(f"checkers: {checkers}")

board_to_json = board_to_json(board_next)
print(f"Board in JSON: {board_to_json}")

