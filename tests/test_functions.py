"""
Sezione 2 - Test Funzionalità Principali
Verifica le funzioni core: is_legal_move, apply_move, detect_move, find_checkers
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.chess_core import (
    json_to_board, is_legal_move, apply_move, detect_move,
    find_checkers, warn_if_in_check
)


class TestPawnMoves:
    
    def test_white_pawn_single_step(self, initial_board):
        assert is_legal_move('P', 'e2', 'e3', initial_board, 'white') == True
    
    def test_white_pawn_double_step_from_start(self, initial_board):
        assert is_legal_move('P', 'e2', 'e4', initial_board, 'white') == True
    
    def test_white_pawn_illegal_triple_step(self, initial_board):
        assert is_legal_move('P', 'e2', 'e5', initial_board, 'white') == False
    
    def test_black_pawn_single_step(self, initial_board):
        assert is_legal_move('p', 'e7', 'e6', initial_board, 'black') == True
    
    def test_black_pawn_double_step_from_start(self, initial_board):
        assert is_legal_move('p', 'e7', 'e5', initial_board, 'black') == True
    
    def test_pawn_blocked_by_piece(self, initial_board):
        blocked = {
            'neri': {'pedoni': ['e5'], 'alfieri': [], 'cavalli': [], 'torri': [], 'regina': [], 're': ['e8']},
            'bianchi': {'pedoni': ['e4'], 'alfieri': [], 'cavalli': [], 'torri': [], 'regina': [], 're': ['e1']}
        }
        board = json_to_board(blocked)
        assert is_legal_move('P', 'e4', 'e5', board, 'white') == False


class TestKnightMoves:
    
    def test_knight_l_shape_move(self, initial_board):
        assert is_legal_move('N', 'g1', 'f3', initial_board, 'white') == True
    
    def test_knight_can_jump_pieces(self, initial_board):
        assert is_legal_move('N', 'b1', 'c3', initial_board, 'white') == True
    
    def test_knight_illegal_straight_move(self, initial_board):
        assert is_legal_move('N', 'g1', 'g3', initial_board, 'white') == False


class TestBishopMoves:
    
    def test_bishop_blocked_at_start(self, initial_board):
        assert is_legal_move('B', 'c1', 'e3', initial_board, 'white') == False
    
    def test_bishop_diagonal_move(self):
        open_board = {
            'neri': {'pedoni': [], 'alfieri': [], 'cavalli': [], 'torri': [], 'regina': [], 're': ['e8']},
            'bianchi': {'pedoni': [], 'alfieri': ['c1'], 'cavalli': [], 'torri': [], 'regina': [], 're': ['e1']}
        }
        board = json_to_board(open_board)
        assert is_legal_move('B', 'c1', 'f4', board, 'white') == True


class TestRookMoves:
    
    def test_rook_blocked_at_start(self, initial_board):
        assert is_legal_move('R', 'a1', 'a3', initial_board, 'white') == False
    
    def test_rook_horizontal_move(self):
        open_board = {
            'neri': {'pedoni': [], 'alfieri': [], 'cavalli': [], 'torri': [], 'regina': [], 're': ['e8']},
            'bianchi': {'pedoni': [], 'alfieri': [], 'cavalli': [], 'torri': ['a4'], 'regina': [], 're': ['e1']}
        }
        board = json_to_board(open_board)
        assert is_legal_move('R', 'a4', 'h4', board, 'white') == True


class TestQueenMoves:
    
    def test_queen_blocked_at_start(self, initial_board):
        assert is_legal_move('Q', 'd1', 'd3', initial_board, 'white') == False
    
    def test_queen_diagonal_move(self):
        open_board = {
            'neri': {'pedoni': [], 'alfieri': [], 'cavalli': [], 'torri': [], 'regina': [], 're': ['e8']},
            'bianchi': {'pedoni': [], 'alfieri': [], 'cavalli': [], 'torri': [], 'regina': ['d4'], 're': ['e1']}
        }
        board = json_to_board(open_board)
        assert is_legal_move('Q', 'd4', 'h8', board, 'white') == True


class TestKingMoves:
    
    def test_king_single_step(self):
        open_board = {
            'neri': {'pedoni': [], 'alfieri': [], 'cavalli': [], 'torri': [], 'regina': [], 're': ['e8']},
            'bianchi': {'pedoni': [], 'alfieri': [], 'cavalli': [], 'torri': [], 'regina': [], 're': ['e4']}
        }
        board = json_to_board(open_board)
        assert is_legal_move('K', 'e4', 'e5', board, 'white') == True
    
    def test_king_illegal_double_step(self):
        open_board = {
            'neri': {'pedoni': [], 'alfieri': [], 'cavalli': [], 'torri': [], 'regina': [], 're': ['e8']},
            'bianchi': {'pedoni': [], 'alfieri': [], 'cavalli': [], 'torri': [], 'regina': [], 're': ['e4']}
        }
        board = json_to_board(open_board)
        assert is_legal_move('K', 'e4', 'e6', board, 'white') == False


class TestApplyMove:
    
    def test_apply_move_updates_board(self, initial_board):
        new_board = apply_move('P', 'e2', 'e4', initial_board)
        assert new_board.at['e', 4] == 'P'
        assert new_board.at['e', 2] == ''


class TestDetectMove:
    
    def test_detect_single_move(self, initial_board):
        new_board = apply_move('P', 'e2', 'e4', initial_board)
        piece, from_sq, to_sq = detect_move(initial_board, new_board)
        assert piece == 'P'
        assert from_sq == 'e2'
        assert to_sq == 'e4'
    
    def test_detect_move_raises_on_unchanged_board(self, initial_board):
        with pytest.raises(ValueError):
            detect_move(initial_board, initial_board)


class TestFindCheckers:
    
    def test_find_rook_checking_white_king(self):
        check_board = {
            'neri': {'pedoni': [], 'alfieri': [], 'cavalli': [], 'torri': ['e8'], 'regina': [], 're': ['a8']},
            'bianchi': {'pedoni': [], 'alfieri': [], 'cavalli': [], 'torri': [], 'regina': [], 're': ['e1']}
        }
        board = json_to_board(check_board)
        checkers = find_checkers(board)
        assert len(checkers) > 0
    
    def test_no_checkers_at_start(self, initial_board):
        checkers = find_checkers(initial_board)
        assert len(checkers) == 0


class TestWarnIfInCheck:
    
    def test_warns_when_king_in_check(self, check_scenario_json):
        board = json_to_board(check_scenario_json)
        warning = warn_if_in_check(board, 'black')
        assert warning is not None
        assert 'under attack' in warning
    
    def test_no_warning_at_start(self, initial_board):
        warning = warn_if_in_check(initial_board, 'white')
        assert warning is None


class TestColorValidation:
    
    def test_white_cannot_move_black_piece(self, initial_board):
        assert is_legal_move('p', 'e7', 'e5', initial_board, 'white') == False
    
    def test_black_cannot_move_white_piece(self, initial_board):
        assert is_legal_move('P', 'e2', 'e4', initial_board, 'black') == False
