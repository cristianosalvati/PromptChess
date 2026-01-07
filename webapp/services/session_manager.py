import os
import uuid
import json
from datetime import datetime
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from urllib.parse import quote_plus
from openai import OpenAI


class GameSession:
    
    def __init__(self, session_id: str, user_id: str, username: str):
        self.session_id = session_id
        self.user_id = user_id
        self.username = username
        self.messages = []
        self.board_state = None
        self.move_history = []
        self.status = 'active'
        self.created_at = datetime.utcnow()
        self.current_turn = 'white'
        
        api_key = os.environ.get('OPENAI_API_KEY')
        if api_key:
            self.openai_client = OpenAI(api_key=api_key)
        else:
            self.openai_client = None
    
    def init_board(self):
        self.board_state = {
            'neri': {
                'pedoni': ['a7','b7','c7','d7','e7','f7','g7','h7'],
                'alfieri': ['c8','f8'],
                'cavalli': ['b8','g8'],
                'torri': ['a8','h8'],
                'regina': ['d8'],
                're': ['e8']
            },
            'bianchi': {
                'pedoni': ['a2','b2','c2','d2','e2','f2','g2','h2'],
                'alfieri': ['c1','f1'],
                'cavalli': ['b1','g1'],
                'torri': ['a1','h1'],
                'regina': ['d1'],
                're': ['e1']
            }
        }
        return self.board_state
    
    def add_system_message(self, content: str):
        self.messages.append({
            'role': 'system',
            'content': content
        })
    
    def add_user_message(self, content: str):
        self.messages.append({
            'role': 'user',
            'content': content
        })
    
    def add_assistant_message(self, content: str):
        self.messages.append({
            'role': 'assistant',
            'content': content
        })
    
    def pop_last_assistant(self):
        for i in range(len(self.messages) - 1, -1, -1):
            if self.messages[i]['role'] == 'assistant':
                return self.messages.pop(i)
        return None
    
    def get_messages(self):
        return self.messages.copy()
    
    def clear_messages(self):
        self.messages = [m for m in self.messages if m['role'] == 'system']
    
    def send_to_llm(self, prompt: str, model: str = 'gpt-4.1-nano', temperature: float = 0.7) -> str:
        if not self.openai_client:
            raise ValueError("OpenAI client not initialized")
        
        self.add_user_message(prompt)
        
        response = self.openai_client.chat.completions.create(
            model=model,
            messages=self.messages,
            temperature=temperature
        )
        
        assistant_content = response.choices[0].message.content
        self.add_assistant_message(assistant_content)
        
        return assistant_content
    
    def apply_move_to_board(self, piece: str, from_sq: str, to_sq: str):
        piece_map = {
            'P': 'pedoni', 'N': 'cavalli', 'B': 'alfieri', 
            'R': 'torri', 'Q': 'regina', 'K': 're',
            'p': 'pedoni', 'n': 'cavalli', 'b': 'alfieri',
            'r': 'torri', 'q': 'regina', 'k': 're'
        }
        
        is_white = piece.isupper()
        side = 'bianchi' if is_white else 'neri'
        piece_type = piece_map.get(piece.upper(), 'pedoni')
        
        if piece_type in self.board_state[side]:
            pieces = self.board_state[side][piece_type]
            if from_sq in pieces:
                pieces.remove(from_sq)
                pieces.append(to_sq)
        
        enemy_side = 'neri' if is_white else 'bianchi'
        for pt in self.board_state[enemy_side]:
            if to_sq in self.board_state[enemy_side][pt]:
                self.board_state[enemy_side][pt].remove(to_sq)
    
    def record_move(self, move: dict, apply_to_board: bool = False):
        piece = move.get('piece', 'P')
        from_sq = move.get('from', '')
        to_sq = move.get('to', '')
        
        if apply_to_board and from_sq and to_sq:
            self.apply_move_to_board(piece, from_sq, to_sq)
        
        self.move_history.append({
            'move_number': len(self.move_history) + 1,
            'player': self.current_turn,
            'piece': piece,
            'from': from_sq,
            'to': to_sq,
            'ai_message': move.get('ai_message', ''),
            'timestamp': datetime.utcnow().isoformat()
        })
        
        self.current_turn = 'black' if self.current_turn == 'white' else 'white'
    
    def end_game(self, result: str):
        self.status = 'completed'
        self.result = result
    
    def to_dict(self):
        return {
            'session_id': self.session_id,
            'user_id': self.user_id,
            'username': self.username,
            'status': self.status,
            'board_state': self.board_state,
            'move_history': self.move_history,
            'current_turn': self.current_turn,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'messages_count': len(self.messages)
        }


class SessionManager:
    
    def __init__(self):
        user = os.environ.get('MONGO_USER', '')
        password = os.environ.get('MONGO_PASSWORD', '')
        
        if not user or not password:
            raise ValueError("MongoDB credentials not configured")
        
        user_escaped = quote_plus(user)
        password_escaped = quote_plus(password)
        
        uri = f'mongodb+srv://{user_escaped}:{password_escaped}@cluster0.ljvmyxi.mongodb.net/?appName=Cluster0'
        
        self.client = MongoClient(uri, server_api=ServerApi('1'))
        self.db = self.client['promptchess']
        self.games_collection = self.db['games']
        self.moves_collection = self.db['moves']
        
        self.active_sessions = {}
    
    def create_game_session(self, user_id: str, username: str) -> GameSession:
        session_id = str(uuid.uuid4())
        
        session = GameSession(session_id, user_id, username)
        session.init_board()
        
        board_json = json.dumps(session.board_state, indent=4)
        session.add_system_message(f'''Regole:
- Tu giochi dalla parte dei Neri.
- Devi rispondere alla mossa proposta dai Bianchi.
Stato scacchiera iniziale: {board_json}''')
        
        session.add_system_message('''Obiettivi:
- Proponi una mossa valida per i Neri.
- Aggiorna lo stato della scacchiera dopo la tua mossa.''')
        
        session.add_system_message('''Output: Restituisci esclusivamente un oggetto JSON con:
- "mossa_proposta" (es. "e7-e5")
- "bianchi" e "neri" aggiornati con le nuove posizioni dei pezzi''')
        
        self.active_sessions[session_id] = session
        
        self.games_collection.insert_one({
            'session_id': session_id,
            'user_id': user_id,
            'username': username,
            'status': 'active',
            'board_state': session.board_state,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        })
        
        return session
    
    def get_session(self, session_id: str) -> GameSession:
        if session_id in self.active_sessions:
            return self.active_sessions[session_id]
        
        game_doc = self.games_collection.find_one({'session_id': session_id})
        if not game_doc:
            return None
        
        session = GameSession(
            session_id=session_id,
            user_id=game_doc.get('user_id', ''),
            username=game_doc.get('username', '')
        )
        session.board_state = game_doc.get('board_state', session.init_board())
        session.status = game_doc.get('status', 'active')
        session.current_turn = game_doc.get('current_turn', 'white')
        
        moves = list(self.moves_collection.find({'session_id': session_id}).sort('move_number', 1))
        session.move_history = [{
            'move_number': m.get('move_number'),
            'player': m.get('player'),
            'piece': m.get('piece'),
            'from': m.get('from'),
            'to': m.get('to'),
            'timestamp': m.get('timestamp', '').isoformat() if hasattr(m.get('timestamp', ''), 'isoformat') else str(m.get('timestamp', ''))
        } for m in moves]
        
        board_json = json.dumps(session.board_state, indent=4)
        session.add_system_message(f'''Regole:
- Tu giochi dalla parte dei Neri.
- Devi rispondere alla mossa proposta dai Bianchi.
Stato scacchiera: {board_json}''')
        session.add_system_message('''Output: Restituisci esclusivamente un oggetto JSON con:
- "mossa_proposta" (es. "e7-e5")
- "bianchi" e "neri" aggiornati''')
        
        self.active_sessions[session_id] = session
        return session
    
    def get_user_sessions(self, username: str) -> list:
        sessions = self.games_collection.find({
            'username': username
        }).sort('created_at', -1).limit(10)
        
        return list(sessions)
    
    def save_session(self, session: GameSession):
        self.games_collection.update_one(
            {'session_id': session.session_id},
            {
                '$set': {
                    'board_state': session.board_state,
                    'status': session.status,
                    'current_turn': session.current_turn,
                    'updated_at': datetime.utcnow()
                }
            }
        )
        
        if session.move_history:
            last_move = session.move_history[-1]
            self.moves_collection.insert_one({
                'session_id': session.session_id,
                'move_number': last_move['move_number'],
                'player': last_move['player'],
                'piece': last_move['piece'],
                'from': last_move['from'],
                'to': last_move['to'],
                'timestamp': datetime.utcnow()
            })
    
    def end_session(self, session_id: str, result: str, winner: str = None):
        session = self.active_sessions.get(session_id)
        if session:
            session.end_game(result)
            
            self.games_collection.update_one(
                {'session_id': session_id},
                {
                    '$set': {
                        'status': 'completed',
                        'result': result,
                        'winner': winner,
                        'completed_at': datetime.utcnow()
                    }
                }
            )
            
            del self.active_sessions[session_id]
    
    def get_active_session_count(self) -> int:
        return len(self.active_sessions)
    
    def close(self):
        self.client.close()
