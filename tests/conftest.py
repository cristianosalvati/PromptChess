import pytest
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.chess_core import json_to_board, board_to_json

@pytest.fixture
def initial_board_json():
    return {
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

@pytest.fixture
def initial_board(initial_board_json):
    return json_to_board(initial_board_json)

@pytest.fixture
def proxy_base_url():
    return 'http://localhost:5000'

@pytest.fixture
def simple_board_json():
    return {
        'neri': {'pedoni': ['d7'], 'alfieri': [], 'cavalli': [], 'torri': [], 'regina': [], 're': ['e8']},
        'bianchi': {'pedoni': ['e4'], 'alfieri': [], 'cavalli': [], 'torri': [], 'regina': [], 're': ['e1']}
    }

@pytest.fixture
def check_scenario_json():
    return {
        'neri': {'pedoni': ['d7'], 'alfieri': [], 'cavalli': [], 'torri': [], 'regina': [], 're': ['e8']},
        'bianchi': {'pedoni': [], 'alfieri': [], 'cavalli': [], 'torri': ['e1'], 'regina': [], 're': ['a1']}
    }
