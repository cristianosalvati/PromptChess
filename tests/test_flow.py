"""
Sezione 5 - Test Flusso Operativo
Verifica il flusso completo: setup, turno umano, turno AI, fine partita
"""
import pytest
import requests
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.chess_core import json_to_board, board_to_json, is_legal_move, apply_move, is_game_active, game_result


class TestSetup:
    
    def test_proxy_server_responds(self, proxy_base_url):
        try:
            r = requests.get(f'{proxy_base_url}/chat/history', timeout=5)
            assert r.status_code == 200
        except requests.exceptions.ConnectionError:
            pytest.skip("Proxy server non in esecuzione")
    
    def test_init_session_with_system_messages(self, proxy_base_url, initial_board_json):
        try:
            system_messages = [
                'Regole: Tu giochi dalla parte dei Neri. Rispondi solo in JSON.',
                'Output: Restituisci un oggetto JSON con mossa_proposta, bianchi, neri.'
            ]
            r = requests.post(f'{proxy_base_url}/chat/init', json={'system_messages': system_messages}, timeout=10)
            assert r.status_code == 200
            data = r.json()
            assert len(data.get('added_system_messages', [])) >= 2
        except requests.exceptions.ConnectionError:
            pytest.skip("Proxy server non in esecuzione")


class TestHumanTurn:
    
    def test_validate_piece_exists(self, initial_board):
        piece_code = 'P'
        from_sq = 'e2'
        file_from, rank_from = from_sq[0], int(from_sq[1])
        assert initial_board.at[file_from, rank_from] == piece_code
    
    def test_validate_legal_move(self, initial_board):
        assert is_legal_move('P', 'e2', 'e4', initial_board, 'white') == True
    
    def test_reject_illegal_move(self, initial_board):
        assert is_legal_move('P', 'e2', 'e5', initial_board, 'white') == False
    
    def test_apply_human_move(self, initial_board):
        new_board = apply_move('P', 'e2', 'e4', initial_board)
        assert new_board.at['e', 4] == 'P'
        assert new_board.at['e', 2] == ''


class TestAITurn:
    
    @pytest.mark.slow
    def test_ai_responds_with_json(self, proxy_base_url, initial_board_json):
        try:
            system_messages = [
                'Regole: Tu giochi dalla parte dei Neri. Rispondi solo in JSON.',
                f'Stato scacchiera: {json.dumps(initial_board_json)}',
                'Output: Restituisci un oggetto JSON con mossa_proposta, bianchi, neri.'
            ]
            requests.post(f'{proxy_base_url}/chat/init', json={'system_messages': system_messages}, timeout=10)
            
            prompt = 'Mossa dei bianchi: e2-e4. Proponi la tua mossa.'
            r = requests.post(f'{proxy_base_url}/chat', json={
                'prompt': prompt,
                'model': 'gpt-4.1-nano',
                'temperature': 0.7
            }, timeout=60)
            
            assert r.status_code == 200
            response_data = r.json()
            ai_response = response_data.get('response', '')
            
            parsed = json.loads(ai_response)
            assert 'mossa_proposta' in parsed
        except requests.exceptions.ConnectionError:
            pytest.skip("Proxy server non in esecuzione")
        except json.JSONDecodeError:
            pytest.fail("AI non ha risposto con JSON valido")


class TestEndGame:
    
    def test_game_active_with_both_kings(self, initial_board):
        assert is_game_active(initial_board) == True
    
    def test_game_ends_without_king(self):
        no_king = {
            'neri': {'pedoni': [], 'alfieri': [], 'cavalli': [], 'torri': [], 'regina': [], 're': []},
            'bianchi': {'pedoni': [], 'alfieri': [], 'cavalli': [], 'torri': [], 'regina': [], 're': ['e1']}
        }
        board = json_to_board(no_king)
        assert is_game_active(board) == False
    
    def test_game_result_displays_winner(self):
        no_black_king = {
            'neri': {'pedoni': [], 'alfieri': [], 'cavalli': [], 'torri': [], 'regina': [], 're': []},
            'bianchi': {'pedoni': [], 'alfieri': [], 'cavalli': [], 'torri': [], 'regina': [], 're': ['e1']}
        }
        board = json_to_board(no_black_king)
        result = game_result(board)
        assert 'White wins' in result
