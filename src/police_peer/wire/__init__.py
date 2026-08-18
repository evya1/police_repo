"""Wire glue: StandInEngine over the existing stage-1 domain.

This module wires the shared transport layer to the role-local domain.
Both peers import the same shared transport code and parameterize by role.
"""

from __future__ import annotations

from dataclasses import dataclass

from common.domain import Board, GameEngine, Role
from common.transport.series import TurnEngine as TurnEngine


@dataclass
class StandInEngine:
    """A turn engine that wraps the existing GameEngine for the series.

    One fresh GameEngine per sub-game.
    """

    natural_role: Role
    board_size: int = 7
    seed: int = 0

    def _fresh_engine(self, sub_game: int) -> GameEngine:
        """Create a fresh GameEngine for the given sub-game."""
        from common.domain.scoring import role_for
        role = role_for(self.natural_role, sub_game + 1)
        board = Board(size=self.board_size)
        position = (0, 0) if role is Role.POLICE else (3, 3)
        return GameEngine(board=board, role=role, position=position)

    def step(self, sub_game: int, role: Role) -> dict:
        """Return a move dict for the given sub-game and role."""
        engine = self._fresh_engine(sub_game)
        legal_moves = engine.legal_moves()
        # STUB: simple deterministic move selection
        move = legal_moves[0] if legal_moves else "STAY"
        engine.apply_own_move(move)
        return {
            "move": move,
            "hint": "I am here",
            "step": engine.step,
            "state": engine.state_string(),
        }

    def observe_barrier(self, cell) -> None:
        """Absorb an opponent-declared barrier."""
        # STUB: placeholder
        pass

    def answer_capture_claim(self, claim) -> dict | None:
        """Answer a capture claim truthfully."""
        # STUB: placeholder
        return None

    def self_captured(self):
        """Check if self was captured."""
        # STUB: placeholder
        return None

    def survived(self) -> bool:
        """Check if thief survived."""
        # STUB: placeholder
        return False
