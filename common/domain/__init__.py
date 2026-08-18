"""Domain layer: pure per-peer game logic (no I/O, no network).

Board geometry, movement legality, barrier placement, capture/terminal
conditions, and the fixed scoring table.  Both peers import this module
and compute identical results from identical inputs.
"""

from common.domain.board import MOVES, ORTHOGONAL, Board, Cell, Move, chebyshev, manhattan
from common.domain.rules import GameEngine, IllegalMoveError
from common.domain.scoring import (
    SCORES,
    SUB_GAMES_PER_SERIES,
    TIE_SCORE,
    ZEROED,
    Outcome,
    Role,
    is_tie_row,
    role_for,
    score_for,
    settled_outcome,
)

__all__ = [
    "Board",
    "Cell",
    "GameEngine",
    "IllegalMoveError",
    "Move",
    "MOVES",
    "Outcome",
    "ORTHOGONAL",
    "Role",
    "SCORES",
    "SUB_GAMES_PER_SERIES",
    "TIE_SCORE",
    "ZEROED",
    "chebyshev",
    "manhattan",
    "is_tie_row",
    "role_for",
    "score_for",
    "settled_outcome",
]
