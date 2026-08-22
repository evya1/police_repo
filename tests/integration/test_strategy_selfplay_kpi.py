"""KPI self-play harness: PoliceBrain vs reference ThiefBrain test double.

TC-P22 — 20 seeded games, role-pinned Police sub-games, shipped config: capture rate
within 35 rounds vs the reference ThiefBrain >= 60%; median rounds-to-capture <= 28;
captures using <= 8 barriers >= 50% (registered evidence, non-authoritative).
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from common.domain.board import Board
from common.domain.rules import GameEngine
from common.domain.scoring import Outcome, Role
from common.transport.series import TurnEngine
from police_peer.scent import make_trail


class DummyBudgets:
    turn_timeout = 30.0
    connect_timeout = 30.0
    poll_interval = 0.005


_terms = {
    "board_size": 7,
    "smell_grid_size": 5,
    "decay_per_step": 0.1,
    "emit_intensity": 0.9,
    "min_center_intensity": 0.5,
    "max_steps": 35,
    "barriers_max": 14,
    "setting": "New York",
    "hint_max_words": 15,
    "axis_origin_corner": "top-left",
    "axis_start_index": 0,
    "thief_start": [3, 3],
    "cop_start": [0, 0],
    "num_games": 6,
}


@dataclass
class KPIResult:
    """One role-pinned Police sub-game row in the KPI ledger."""

    sub_game: int
    outcome: Outcome
    steps: int
    barriers_used: int
    captured: bool


class RandomThiefEngine(TurnEngine):
    """Reference baseline ThiefBrain test double: uniformly random legal moves."""

    def __init__(self, rng: random.Random) -> None:
        self._rng = rng
        self._engine: GameEngine | None = None
        self._trail = None
        self._pending_claim: tuple | None = None
        self._pending_claim_position: tuple | None = None  # snapshot at claim receipt
        self._thief_caught, self._opponent_terminal = False, None

    def start_subgame(self, sub_game: int, role: Role, terms: dict | None = None) -> None:
        t = terms or {}
        self._engine = GameEngine(
            board=Board(size=int(t.get("board_size", 7))),
            role=role,
            position=(3, 3) if role is Role.THIEF else (0, 0),
            max_steps=int(t.get("max_steps", 35)),
            survival_threshold=int(t.get("survival_threshold", t.get("max_steps", 35))),
            barriers_max=int(t.get("barriers_max", 14)),
        )
        self._pending_claim = self._pending_claim_position = None
        self._thief_caught = False
        self._opponent_terminal = None
        self._trail = make_trail(
            board_size=int(t.get("board_size", 7)),
            field_size=int(t.get("smell_grid_size", 5)),
            decay_per_step=float(t.get("decay_per_step", 0.1)),
            emit_intensity=float(t.get("emit_intensity", 0.9)),
            min_center_intensity=float(t.get("min_center_intensity", 0.5)),
        )

    def decide(self) -> dict:
        if self._engine is None:
            raise RuntimeError("start_subgame must be called before decide")
        legal = self._engine.legal_moves()
        move = self._rng.choice(legal)
        self._engine.apply_own_move(move)
        res: dict = {
            "move": move,
            "hint": "I am evading",
            "state": self._engine.state_string(),
        }
        if self._trail is not None:
            res["smell_grid"] = self._trail.full_turn(self._engine.position)
        if self._engine.role is Role.THIEF:
            if self._pending_claim is not None:
                ans = self._engine.answer_capture_claim(self._pending_claim, at=self._pending_claim_position)
                res["claim_response"] = ans
                self._pending_claim = self._pending_claim_position = None
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
        if self._engine is None:
            return
        if "barrier_placed" in message:
            self._engine.observe_barrier(message["barrier_placed"])
        if self._engine.role is Role.THIEF and "capture_claim" in message:
            cc = message["capture_claim"]
            self._pending_claim = tuple(cc) if isinstance(cc, list) else cc
            self._pending_claim_position = self._engine.position
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

    def terminal_final(self) -> dict | None:
        if self._engine is None:
            return None
        eng = self._engine
        if eng.role is Role.THIEF:
            # Concession for the capture only this side can see (rules 46/47); the
            # reference sends a fresh scent field on the caught final.
            if eng.self_captured() is None:
                return None
            eng.apply_own_move("STAY")
            res = {
                "move": "STAY",
                "hint": "",
                "state": eng.state_string(),
                "claim_response": {"claim": [int(eng.position[0]), int(eng.position[1])],
                                   "caught": True},
            }
            if self._trail is not None:
                res["smell_grid"] = self._trail.full_turn(eng.position)
            return res
        if self.terminal() is None:
            return None
        eng.apply_own_move("STAY")
        return {"move": "STAY", "hint": "", "state": eng.state_string()}
