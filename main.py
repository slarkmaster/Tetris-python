#!/usr/bin/env python3
"""Tetris.

Install (from this folder):

    python3 -m venv .venv
    source .venv/bin/activate
    python -m pip install -r requirements.txt

Run:

    python main.py
"""

import random

from tetris.app import Session, main
from tetris.board import Piece, cells_fit, empty_board
from tetris.bot import BOT_WEIGHTS, choose_move, evaluate_board
from tetris.constants import (
    ATTACK_LINES,
    COLS,
    GARBAGE_FLIGHT_MS,
    GARBAGE_RISE_MS,
    ROWS,
    SHAPES,
    SPAWN_X,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
)
from tetris.controls import KeyBindings, KeyboardSettings
from tetris.game import Game
from tetris.ui import draw_board, draw_versus, make_fonts
from tetris.versus import Versus, exchange_attacks

if __name__ == "__main__":
    main()
