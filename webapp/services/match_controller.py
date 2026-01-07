import json
import copy
import random
from abc import ABC, abstractmethod

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from modules.chess_core import (
    json_to_board, board_to_json, is_legal_move, 
    detect_move, apply_move, boards_equal, 
    warn_if_in_check, is_game_active, game_result
)


class MatchObserver(ABC):
    @abstractmethod
    def on_move_committed(self, player, piece, from_sq, to_sq, board_state, metadata=None):
        pass
    
    @abstractmethod
    def on_error(self, message):
        pass
    
    @abstractmethod
    def on_game_over(self, result, board_state):
        pass


class MatchController:
    MAX_RETRIES = 3
    
    def __init__(self, initial_board_json, llm_func, observer=None):
        self.board_prev = json_to_board(initial_board_json)
        self.llm_func = llm_func
        self.observer = observer
        self.is_human_turn = True
        self.last_human_move = None
        self.conversation_history = []
    
    def get_board_json(self):
        return board_to_json(self.board_prev)
    
    def submit_human_move(self, piece_code, from_sq, to_sq):
        if not self.is_human_turn:
            return {'success': False, 'error': 'Not your turn'}
        
        from_sq = from_sq.lower()
        to_sq = to_sq.lower()
        
        file_from, rank_from = from_sq[0], int(from_sq[1])
        actual_piece = self.board_prev.at[file_from, rank_from]
        
        if actual_piece == '':
            return {'success': False, 'error': f'No piece at {from_sq}'}
        
        if actual_piece != piece_code.upper():
            return {'success': False, 'error': f"No piece '{piece_code}' at {from_sq}, found '{actual_piece}'"}
        
        if not is_legal_move(piece_code, from_sq, to_sq, self.board_prev, "white"):
            return {'success': False, 'error': f'Illegal move: {piece_code} {from_sq}->{to_sq}'}
        
        board_next = apply_move(piece_code, from_sq, to_sq, self.board_prev)
        
        check_warning = warn_if_in_check(board_next, "white")
        if check_warning is not None:
            return {'success': False, 'error': check_warning}
        
        self.board_prev = board_next
        self.last_human_move = f"{from_sq}-{to_sq}"
        self.is_human_turn = False
        
        if self.observer:
            self.observer.on_move_committed(
                player='white',
                piece=piece_code,
                from_sq=from_sq,
                to_sq=to_sq,
                board_state=board_to_json(self.board_prev),
                metadata=None
            )
        
        if not is_game_active(self.board_prev):
            result = game_result(self.board_prev)
            if self.observer:
                self.observer.on_game_over(result, board_to_json(self.board_prev))
            return {'success': True, 'game_over': True, 'result': result}
        
        return {'success': True}
    
    def request_ai_move(self):
        if self.is_human_turn:
            return {'success': False, 'error': 'Not AI turn'}
        
        board_json = board_to_json(self.board_prev)
        
        prompt = f'''
Mossa dei Bianchi: {self.last_human_move}
Stato scacchiera attuale (già aggiornato con la mossa dei Bianchi):
{json.dumps(board_json, indent=2)}

Proponi la tua mossa per i Neri e aggiorna lo stato della scacchiera.
Rispondi in JSON con: neri, bianchi, mossa_proposta, commento_giocatore, messaggio_avversario.
'''
        
        last_error = ''
        
        for attempt in range(self.MAX_RETRIES):
            temperature = random.uniform(0.70, 0.95)
            
            try:
                ai_response = self.llm_func(prompt, temperature=temperature)
            except Exception as e:
                last_error = str(e)
                continue
            
            if ai_response is None:
                last_error = 'No response from AI'
                continue
            
            try:
                parsed = json.loads(ai_response)
            except json.JSONDecodeError:
                last_error = 'Invalid JSON'
                prompt = f"La tua risposta non era JSON valido. Riprova: {json.dumps(board_json)}"
                continue
            
            if 'neri' not in parsed or 'bianchi' not in parsed:
                last_error = 'Missing neri/bianchi in response'
                prompt = f"Manca la definizione di neri/bianchi. Stato attuale: {json.dumps(board_json)}"
                continue
            
            ai_board_json = {'neri': parsed['neri'], 'bianchi': parsed['bianchi']}
            
            try:
                board_next = json_to_board(ai_board_json)
            except Exception as e:
                last_error = f'Invalid board structure: {e}'
                prompt = f"Struttura board invalida. Stato attuale: {json.dumps(board_json)}"
                continue
            
            try:
                detected = detect_move(self.board_prev, board_next)
                piece, from_sq, to_sq = detected
            except Exception as e:
                mossa_proposta = parsed.get('mossa_proposta', '')
                if mossa_proposta and '-' in mossa_proposta:
                    parts = mossa_proposta.replace('-', ' ').split()
                    if len(parts) >= 2:
                        from_sq = parts[0].lower()
                        to_sq = parts[1].lower()
                        
                        if boards_equal(self.board_prev, board_next):
                            if is_legal_move(None, from_sq, to_sq, self.board_prev, "black"):
                                correct_board = apply_move(None, from_sq, to_sq, self.board_prev)
                                correct_json = board_to_json(correct_board)
                                prompt = f"La board non è stata aggiornata dopo la mossa '{mossa_proposta}'. Aggiorna così: {json.dumps(correct_json)}"
                                continue
                
                last_error = f'Cannot detect move: {e}'
                prompt = f"Non riesco a rilevare la mossa. Proponi una mossa valida per i Neri e aggiorna la board: {json.dumps(board_json)}"
                continue
            
            if not is_legal_move(piece, from_sq, to_sq, self.board_prev, "black"):
                last_error = f'Illegal move: {piece} {from_sq}->{to_sq}'
                prompt = f"Mossa illegale '{from_sq}->{to_sq}'. Proponi una mossa valida per i Neri. Stato: {json.dumps(board_json)}"
                continue
            
            verified_board = apply_move(piece, from_sq, to_sq, self.board_prev)
            
            if not boards_equal(verified_board, board_next):
                last_error = 'Board state mismatch after applying move'
                correct_json = board_to_json(verified_board)
                prompt = f"Lo stato della board non corrisponde alla mossa. Stato corretto dopo la mossa: {json.dumps(correct_json)}"
                continue
            
            check_warning = warn_if_in_check(board_next, "black", (piece, from_sq, to_sq))
            if check_warning is not None:
                last_error = check_warning
                prompt = f"{check_warning} - Proponi una mossa che non lasci il Re nero sotto scacco. Stato: {json.dumps(board_json)}"
                continue
            
            self.board_prev = board_next
            self.is_human_turn = True
            
            ai_comment = parsed.get('commento_giocatore', '')
            ai_message = parsed.get('messaggio_avversario', '')
            mossa_proposta = parsed.get('mossa_proposta', f'{from_sq}-{to_sq}')
            
            if self.observer:
                self.observer.on_move_committed(
                    player='black',
                    piece=piece,
                    from_sq=from_sq,
                    to_sq=to_sq,
                    board_state=board_to_json(self.board_prev),
                    metadata={
                        'ai_comment': ai_comment,
                        'ai_message': ai_message,
                        'mossa_proposta': mossa_proposta
                    }
                )
            
            if not is_game_active(self.board_prev):
                result = game_result(self.board_prev)
                if self.observer:
                    self.observer.on_game_over(result, board_to_json(self.board_prev))
                return {
                    'success': True,
                    'game_over': True,
                    'result': result,
                    'ai_move': f'{from_sq}-{to_sq}',
                    'ai_comment': ai_comment,
                    'ai_message': ai_message,
                    'board_state': board_to_json(self.board_prev)
                }
            
            return {
                'success': True,
                'ai_move': f'{from_sq}-{to_sq}',
                'ai_comment': ai_comment,
                'ai_message': ai_message,
                'board_state': board_to_json(self.board_prev)
            }
        
        if self.observer:
            self.observer.on_error(f'AI failed after {self.MAX_RETRIES} attempts: {last_error}')
        
        return {
            'success': False,
            'error': f'AI failed after {self.MAX_RETRIES} attempts: {last_error}',
            'board_state': board_to_json(self.board_prev)
        }
