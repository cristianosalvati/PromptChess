"""
Sezione 6 - Test Gestione Hallucinations e Resilienza
Verifica contromisure: JSON repair, validazione mosse, rollback, feedback
"""
import pytest
import requests
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.chess_core import (
    json_to_board, boards_equal, repair_json_board,
    is_legal_move, detect_move, warn_if_in_check
)


class TestUnchangedBoardDetection:
    
    def test_detects_unchanged_board(self, initial_board_json):
        board1 = json_to_board(initial_board_json)
        board2 = json_to_board(initial_board_json)
        assert boards_equal(board1, board2) == True
    
    def test_detect_move_raises_on_unchanged(self, initial_board_json):
        board = json_to_board(initial_board_json)
        with pytest.raises(ValueError):
            detect_move(board, board)


class TestMalformedJsonRepair:
    
    def test_repair_code_fences(self):
        malformed = '```json\n{"mossa_proposta": "e7-e5"}\n```'
        repaired = repair_json_board(malformed)
        parsed = json.loads(repaired)
        assert parsed['mossa_proposta'] == 'e7-e5'
    
    def test_repair_missing_braces(self):
        malformed = '{"mossa_proposta": "e7-e5", "neri": {"pedoni": ["e5"]'
        repaired = repair_json_board(malformed)
        parsed = json.loads(repaired)
        assert 'mossa_proposta' in parsed
    
    def test_repair_triple_backticks(self):
        malformed = '```\n{"mossa_proposta": "d7-d5"}\n```'
        repaired = repair_json_board(malformed)
        parsed = json.loads(repaired)
        assert parsed['mossa_proposta'] == 'd7-d5'


class TestIllegalMoveDetection:
    
    def test_rejects_pawn_triple_jump(self, initial_board):
        assert is_legal_move('p', 'e7', 'e4', initial_board, 'black') == False
    
    def test_rejects_knight_straight_move(self, initial_board):
        assert is_legal_move('N', 'g1', 'g3', initial_board, 'white') == False
    
    def test_rejects_blocked_move(self, initial_board):
        assert is_legal_move('R', 'a1', 'a3', initial_board, 'white') == False


class TestRoleConfusion:
    
    def test_black_cannot_move_white_piece(self, initial_board):
        assert is_legal_move('P', 'e2', 'e4', initial_board, 'black') == False
    
    def test_white_cannot_move_black_piece(self, initial_board):
        assert is_legal_move('p', 'e7', 'e5', initial_board, 'white') == False


class TestAutoCheckDetection:
    
    def test_detects_king_under_attack(self, check_scenario_json):
        board = json_to_board(check_scenario_json)
        warning = warn_if_in_check(board, 'black')
        assert warning is not None
        assert 'under attack' in warning


class TestProxyContromisure:
    
    def test_rollback_last_assistant(self, proxy_base_url):
        try:
            system_messages = ['Test message']
            requests.post(f'{proxy_base_url}/chat/init', json={'system_messages': system_messages}, timeout=5)
            requests.post(f'{proxy_base_url}/chat', json={
                'prompt': 'Test prompt',
                'model': 'gpt-4.1-nano',
                'temperature': 0.5
            }, timeout=30)
            
            r = requests.post(f'{proxy_base_url}/chat/pop/assistant', timeout=5)
            assert r.status_code == 200
        except requests.exceptions.ConnectionError:
            pytest.skip("Proxy server non in esecuzione")
    
    def test_append_feedback_message(self, proxy_base_url):
        try:
            feedback = '[Illegal move proposed. Please try again.]'
            r = requests.post(f'{proxy_base_url}/chat/append', json={
                'role': 'user',
                'content': feedback
            }, timeout=5)
            assert r.status_code == 200
        except requests.exceptions.ConnectionError:
            pytest.skip("Proxy server non in esecuzione")
    
    def test_history_contains_system_messages(self, proxy_base_url):
        try:
            system_messages = ['Regole JSON', 'Output format']
            requests.post(f'{proxy_base_url}/chat/init', json={'system_messages': system_messages}, timeout=5)
            
            r = requests.get(f'{proxy_base_url}/chat/history', timeout=5)
            history = r.json()
            system_msgs = [m for m in history if m.get('role') == 'system']
            assert len(system_msgs) >= 2
        except requests.exceptions.ConnectionError:
            pytest.skip("Proxy server non in esecuzione")


class TestModelUpgrade:
    
    def test_model_gear_chain(self):
        model_map = {
            0: 'gpt-4o-mini',
            1: 'gpt-4o',
            2: 'gpt-4.1-nano',
            3: 'gpt-4.1-mini',
            4: 'o4-mini',
            5: 'gpt-4.1'
        }
        
        current_gear = 2
        next_gear = current_gear + 1
        next_model = model_map.get(next_gear)
        
        assert next_model == 'gpt-4.1-mini'
        assert len(model_map) == 6
