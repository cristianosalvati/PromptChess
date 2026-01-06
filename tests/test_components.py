"""
Sezione 3 - Test Componenti
Verifica i moduli principali: chess_core, openai_proxy_service, ChatSession
"""
import pytest
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.chess_core import (
    json_to_board, board_to_json, is_legal_move, apply_move,
    detect_move, find_checkers, warn_if_in_check, boards_equal,
    repair_json_board, is_game_active, game_result
)


class TestChessCore:
    
    def test_json_to_board_creates_dataframe(self, initial_board_json):
        board = json_to_board(initial_board_json)
        assert board is not None
        assert hasattr(board, 'columns')
        assert len(board.columns) == 8
    
    def test_board_to_json_roundtrip(self, initial_board_json):
        board = json_to_board(initial_board_json)
        result = board_to_json(board)
        assert 'neri' in result
        assert 'bianchi' in result
        assert 'pedoni' in result['neri']
        assert 'pedoni' in result['bianchi']
    
    def test_board_has_correct_pieces_count(self, initial_board):
        white_pieces = 0
        black_pieces = 0
        for col in initial_board.columns:
            for val in initial_board[col]:
                if val and val.isupper():
                    white_pieces += 1
                elif val and val.islower():
                    black_pieces += 1
        assert white_pieces == 16
        assert black_pieces == 16


class TestBoardsEqual:
    
    def test_identical_boards_are_equal(self, initial_board_json):
        board1 = json_to_board(initial_board_json)
        board2 = json_to_board(initial_board_json)
        assert boards_equal(board1, board2) == True
    
    def test_different_boards_not_equal(self, initial_board_json):
        board1 = json_to_board(initial_board_json)
        modified = initial_board_json.copy()
        modified['bianchi'] = initial_board_json['bianchi'].copy()
        modified['bianchi']['pedoni'] = ['a2','b2','c2','d2','e4','f2','g2','h2']
        board2 = json_to_board(modified)
        assert boards_equal(board1, board2) == False


class TestRepairJsonBoard:
    
    def test_removes_code_fences(self):
        malformed = '```json\n{"mossa_proposta": "e7-e5"}\n```'
        repaired = repair_json_board(malformed)
        parsed = json.loads(repaired)
        assert parsed['mossa_proposta'] == 'e7-e5'
    
    def test_adds_missing_braces(self):
        malformed = '{"mossa_proposta": "e7-e5", "neri": {"pedoni": ["e5"]'
        repaired = repair_json_board(malformed)
        parsed = json.loads(repaired)
        assert 'mossa_proposta' in parsed
    
    def test_clean_json_unchanged(self):
        clean = '{"mossa_proposta": "e7-e5"}'
        repaired = repair_json_board(clean)
        assert json.loads(repaired) == json.loads(clean)


class TestGameState:
    
    def test_game_active_with_both_kings(self, initial_board):
        assert is_game_active(initial_board) == True
    
    def test_game_inactive_without_black_king(self):
        no_black_king = {
            'neri': {'pedoni': [], 'alfieri': [], 'cavalli': [], 'torri': [], 'regina': [], 're': []},
            'bianchi': {'pedoni': [], 'alfieri': [], 'cavalli': [], 'torri': [], 'regina': [], 're': ['e1']}
        }
        board = json_to_board(no_black_king)
        assert is_game_active(board) == False
    
    def test_game_result_white_wins(self):
        no_black_king = {
            'neri': {'pedoni': [], 'alfieri': [], 'cavalli': [], 'torri': [], 'regina': [], 're': []},
            'bianchi': {'pedoni': [], 'alfieri': [], 'cavalli': [], 'torri': [], 'regina': [], 're': ['e1']}
        }
        board = json_to_board(no_black_king)
        result = game_result(board)
        assert 'White wins' in result
