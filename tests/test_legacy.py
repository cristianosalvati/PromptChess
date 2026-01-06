"""
Test Legacy - Migrato da modules/chess_test.py
Test originali di detect_move e is_legal_move
"""
import pytest
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.chess_core import json_to_board, board_to_json, is_legal_move, detect_move, find_checkers


class TestLegacyDetectMove:
    
    @pytest.fixture
    def legacy_prev_state(self):
        return {
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
            }
        }
    
    @pytest.fixture
    def legacy_next_state(self):
        return {
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
    
    def test_detect_pawn_move(self, legacy_prev_state, legacy_next_state):
        board_prev = json_to_board(legacy_prev_state)
        board_next = json_to_board(legacy_next_state)
        
        piece, from_sq, to_sq = detect_move(board_prev, board_next)
        
        assert piece == 'P'
        assert from_sq == 'b2'
        assert to_sq == 'b3'
    
    def test_move_legality(self, legacy_prev_state):
        board = json_to_board(legacy_prev_state)
        legal = is_legal_move('P', 'b2', 'b3', board)
        assert legal == True
    
    def test_find_checkers_in_scenario(self, legacy_prev_state):
        board = json_to_board(legacy_prev_state)
        checkers = find_checkers(board)
        assert isinstance(checkers, list)
    
    def test_board_to_json_output(self, legacy_next_state):
        board = json_to_board(legacy_next_state)
        result = board_to_json(board)
        
        assert 'neri' in result
        assert 'bianchi' in result
        assert 'b3' in result['bianchi']['pedoni']
