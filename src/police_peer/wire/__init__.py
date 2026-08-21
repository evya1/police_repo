"""Wire glue: StandInEngine over the existing stage-1 domain.

This module wires the shared transport layer to the role-local domain.
Both peers import the same shared transport code and parameterize by role.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from common.domain.board import Board
from common.domain.rules import GameEngine
from common.domain.scoring import Outcome, Role
from common.transport.series import TurnEngine


@dataclass
class StandInEngine:
    """A stateful turn engine using GameEngine for the series."""

    natural_role: Role
    board_size: int = 7
    seed: int = 0

    _engine: GameEngine | None = None
    _opponent_terminal: Outcome | None = None
    _pending_claim: tuple | None = None

    def start_subgame(self, sub_game: int, role: Role) -> None:
        """Create a fresh GameEngine for the given sub-game."""
        board = Board(size=self.board_size)
        position = (0, 0) if role is Role.POLICE else (3, 3)
        self._engine = GameEngine(board=board, role=role, position=position)
        self._opponent_terminal = None
        self._pending_claim = None

    def decide(self) -> dict:
        """Return a move dict for the current sub-game and role."""
        legal_moves = self._engine.legal_moves()
        move = legal_moves[0] if legal_moves else "STAY"
        self._engine.apply_own_move(move)

        res: dict[str, Any] = {
            "move": move,
            "hint": "I am here",
            "state": self._engine.state_string(),
        }

        if self._engine.role is Role.POLICE:
            pass # No random capture_claim

        if self._engine.role is Role.THIEF:
            if self._pending_claim is not None:
                res["claim_response"] = self._engine.answer_capture_claim(self._pending_claim)
                self._pending_claim = None
            if self._engine.survived():
                res["win_claim"] = {"type": "survival"}
            elif self._engine.self_captured():
                res["win_claim"] = {"type": "capture"}

        return res

    def observe_opponent(self, message: dict) -> None:
        """Absorb an opponent's turn message."""
        if "barrier_placed" in message:
            self._engine.observe_barrier(message["barrier_placed"])

        if self._engine.role is Role.THIEF:
            if "capture_claim" in message:
                self._pending_claim = tuple(message["capture_claim"]) if isinstance(message["capture_claim"], list) else message["capture_claim"]

        if self._engine.role is Role.POLICE:
            if "claim_response" in message:
                if message["claim_response"].get("caught") is True:
                    self._opponent_terminal = Outcome.CAPTURE
            if "win_claim" in message:
                if message["win_claim"].get("type") == "survival":
                    self._opponent_terminal = Outcome.SURVIVAL
                elif message["win_claim"].get("type") == "capture":
                    self._opponent_terminal = Outcome.CAPTURE

    def terminal(self) -> Outcome | None:
        """Return terminal outcome if reached."""
        if self._opponent_terminal is not None:
            return self._opponent_terminal
        if self._engine.role is Role.THIEF:
            if self._engine.self_captured():
                return Outcome.CAPTURE
            if self._engine.survived():
                return Outcome.SURVIVAL
        return None

