"""Police peer wire adapter and baseline turn engine.

Both peers import the same shared transport code and parameterize by role.
"""

from __future__ import annotations

from dataclasses import dataclass, field
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
    strategy: Any = None

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
        if role is Role.POLICE:
            cop_start = t.get("cop_start", (0, 0))
            position = tuple(cop_start) if isinstance(cop_start, (list, tuple)) else (0, 0)
        else:
            thief_start = t.get("thief_start", (3, 3))
            position = tuple(thief_start) if isinstance(thief_start, (list, tuple)) else (3, 3)
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
        if self.strategy is not None and hasattr(self.strategy, "select_action"):
            view = {
                "role": self._engine.role.value,
                "position": list(self._engine.position),
                "step": self._engine.step,
                "barriers": [list(b) for b in self._engine.barriers],
            }
            move = self.strategy.select_action(legal_moves, view)
            if move not in legal_moves:
                move = legal_moves[0] if legal_moves else "STAY"
        else:
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

    def terminal_final(self) -> dict | None:
        """The game-ending final step owed after settling, or None.

        A thief that saw its own capture (rules 46/47 — a fact only the thief can
        see) owes a concession: a STAY naming its own final cell with caught=true.
        An answered claim or a survival claim already rode the last normal step, so
        only the invisible capture needs the extra sealed final. A police settling
        from the thief's final owes a plain sealed STAY.
        """
        if self._engine is None:
            return None
        eng = self._engine
        if eng.role is Role.THIEF:
            if eng.self_captured() is None:
                return None
            eng.apply_own_move("STAY")
            return {
                "move": "STAY",
                "hint": "",
                "state": eng.state_string(),
                "claim_response": {"claim": [int(eng.position[0]), int(eng.position[1])],
                                   "caught": True},
            }
        if self.terminal() is None:
            return None
        eng.apply_own_move("STAY")
        return {"move": "STAY", "hint": "", "state": eng.state_string()}


@dataclass
class BrainDrivenEngine(StandInEngine):
    """TurnEngine seam: real PoliceBrain on POLICE sub-games, stand-in on THIEF.

    S3a: resolve_brain(config, role) per sub-game + brain.decide(...) +
    when barrier_cell is set: engine.place_own_barrier(barrier_cell) then
    engine.apply_own_move(action) + the frame's barrier_placed field (GAME-012).
    S3b: the outgoing frame's hint comes from Decision.hint (template writer).
    S3c: brain.note_evidence(smell_grid) on each received turn, before the
    decision (SD-P5).

    THIEF sub-games keep the stand-in selection on the existing path (SD-P7).
    """

    config: dict | None = None
    _brain: Any = None
    _belief: Any = None
    _last_field: dict[str, float] = field(default_factory=dict)
    _last_opponent_hint: str = ""
    _arena: str = "New York"

    def start_subgame(self, sub_game: int, role: Role, terms: dict | None = None) -> None:
        """Create a fresh GameEngine and, on POLICE sub-games, a fresh brain + belief."""
        super().start_subgame(sub_game, role, terms)
        self._brain = None
        self._belief = None
        self._last_field = {}
        self._last_opponent_hint = ""
        cfg = self.config or {}
        world = cfg.get("world")
        self._arena = str(world.get("map_area", "New York")) if isinstance(world, dict) else "New York"
        if role is Role.POLICE:
            from police_peer.belief import build_belief
            from police_peer.strategy import resolve_brain

            self._brain = resolve_brain(cfg, role)
            self._brain.reset(self._engine.position)
            self._belief = build_belief(self._engine.board, cfg, probe=None)

    def decide(self) -> dict:
        """Return a move dict. POLICE sub-games are brain-driven; THIEF keep the stand-in."""
        if self._engine is None:
            raise RuntimeError("start_subgame must be called before decide")

        if self._brain is not None:
            self._brain.note_evidence(self._last_field)
            decision = self._brain.decide(
                self._engine, self._belief, self._last_opponent_hint, self._arena,
            )
            # Barrier first: place barrier if decided, then apply move (FR-P2/FR-P4).
            if decision.barrier_cell is not None:
                self._engine.place_own_barrier(decision.barrier_cell)
            self._engine.apply_own_move(decision.action)
            res: dict[str, Any] = {
                "move": decision.action,
                "hint": decision.hint,
                "state": self._engine.state_string(),
            }
            if decision.barrier_cell is not None:
                res["barrier_placed"] = list(decision.barrier_cell)
            # THIEF-side claim handling (for completeness when brain is active).
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

        return super().decide()

    def observe_opponent(self, message: dict) -> None:
        """Absorb an opponent's turn message; feed scent + hint into the belief."""
        if "smell_grid" in message:
            self._last_field = dict(message["smell_grid"])
            if self._belief is not None:
                self._belief.observe_smell(self._last_field)
        if "hint" in message:
            self._last_opponent_hint = str(message["hint"])
            if self._belief is not None:
                self._belief.apply_hint(self._last_opponent_hint, self._arena)
        super().observe_opponent(message)
