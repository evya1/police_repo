"""Police peer wire adapter and baseline turn engine.

Both peers import the same shared transport code and parameterize by role.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from common.domain.board import Board
from common.domain.rules import GameEngine
from common.domain.scoring import Outcome, Role
from common.transport.series import TurnEngine as TurnEngine


@dataclass
class StandInEngine:
    """A stateful turn engine using GameEngine for the series."""

    natural_role: Role
    board_size: int = 7
    seed: int = 0
    terms: dict | None = None

    _engine: GameEngine | None = None
    _opponent_terminal: Outcome | None = None
    _pending_claim: tuple | None = None
    _thief_caught: bool = False

    def start_subgame(self, sub_game: int, role: Role, terms: dict | None = None) -> None:
        """Create a fresh GameEngine for the given sub-game."""
        t = terms or self.terms or {}
        board_size = t.get("board_size", self.board_size)
        max_steps = int(t.get("max_steps", 35))
        survival_threshold = int(t.get("survival_threshold", max_steps))
        max_moves = int(t.get("max_moves", max_steps))
        barriers_max = int(t.get("barriers_max", 14))

        if max_moves != survival_threshold or max_steps != survival_threshold:
            raise ValueError(
                f"divergent max_moves/max_steps ({max_steps}) and survival_threshold "
                f"({survival_threshold}) refused (OPEN-011)"
            )

        board = Board(size=board_size)
        position = (0, 0) if role is Role.POLICE else (3, 3)
        self._engine = GameEngine(
            board=board,
            role=role,
            position=position,
            max_steps=max_steps,
            survival_threshold=survival_threshold,
            barriers_max=barriers_max,
        )
        self._opponent_terminal = None
        self._pending_claim = None
        self._thief_caught = False

    def decide(self) -> dict:
        """Return a move dict for the current sub-game and role."""
        if self._engine is None:
            raise RuntimeError("start_subgame must be called before decide")

        legal_moves = self._engine.legal_moves()
        move = legal_moves[0] if legal_moves else "STAY"
        self._engine.apply_own_move(move)

        res: dict[str, Any] = {
            "move": move,
            "hint": "I am here",
            "state": self._engine.state_string(),
        }

        if self._engine.role is Role.POLICE:
            pass

        if self._engine.role is Role.THIEF:
            if self._pending_claim is not None:
                ans = self._engine.answer_capture_claim(self._pending_claim)
                res["claim_response"] = ans
                self._pending_claim = None
                if ans and ans.get("caught") is True:
                    self._thief_caught = True
                    res["win_claim"] = {"type": "capture"}
                    return res

            if self._engine.self_captured():
                res["win_claim"] = {"type": "capture"}
            elif self._engine.survived():
                res["win_claim"] = {"type": "survival"}

        return res

    def observe_opponent(self, message: dict) -> None:
        """Absorb an opponent's turn message."""
        if self._engine is None:
            return

        if "barrier_placed" in message:
            self._engine.observe_barrier(message["barrier_placed"])

        if self._engine.role is Role.THIEF and "capture_claim" in message:
            cc = message["capture_claim"]
            self._pending_claim = tuple(cc) if isinstance(cc, list) else cc

        if self._engine.role is Role.POLICE:
            if "claim_response" in message and message["claim_response"].get("caught") is True:
                self._opponent_terminal = Outcome.CAPTURE
            win_claim = message.get("win_claim")
            if win_claim:
                wtype = win_claim.get("type")
                if wtype == "survival":
                    self._opponent_terminal = Outcome.SURVIVAL
                elif wtype == "capture":
                    self._opponent_terminal = Outcome.CAPTURE

    def terminal(self) -> Outcome | None:
        """Return terminal outcome if reached."""
        if self._opponent_terminal is not None:
            return self._opponent_terminal
        if self._thief_caught:
            return Outcome.CAPTURE
        if self._engine is not None and self._engine.role is Role.THIEF:
            if self._engine.self_captured():
                return Outcome.CAPTURE
            if self._engine.survived():
                return Outcome.SURVIVAL
        return None
