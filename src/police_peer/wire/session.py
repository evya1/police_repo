"""SubgameSession — the mutable game lifecycle shared by both wire adapters.

Neither ``StandInEngine`` nor ``BrainDrivenEngine`` subclasses the other;
both compose one of these. It owns exactly what is genuinely shared: the
fresh-per-sub-game ``GameEngine``, this peer's own outgoing scent trail,
capture-claim bookkeeping, and terminal-state tracking.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from common.domain.board import Board, Cell
from common.domain.rules import GameEngine
from common.domain.scoring import Outcome, Role
from police_peer.scent.model import Trail, make_trail


@dataclass
class SubgameSession:
    """Shared mutable lifecycle: engine, own trail, claims, terminal state."""

    natural_role: Role
    board_size: int = 7
    seed: int = 0
    scent_model: str | None = None

    engine: GameEngine | None = None
    trail: Trail | None = None
    opponent_terminal: Outcome | None = None
    pending_claim: tuple | None = None
    pending_claim_position: Cell | None = None
    thief_caught: bool = False

    def start(self, sub_game: int, role: Role, terms: dict | None = None) -> GameEngine:
        """Fresh GameEngine + fresh own-scent Trail for this sub-game. No leaked state."""
        t = terms or {}
        board_size = t.get("board_size", self.board_size)
        max_steps = int(t.get("max_steps", 35))
        survival_threshold = int(t.get("survival_threshold", max_steps))
        max_moves = int(t.get("max_moves", max_steps))
        barriers_max = int(t.get("barriers_max", 14))

        if max_moves != survival_threshold or max_steps != survival_threshold:
            raise ValueError(
                f"divergent max_moves/max_steps ({max_steps}) and survival_threshold "
                f"({survival_threshold}) refused by the production termination contract"
            )

        board = Board(size=board_size)
        if role is Role.POLICE:
            cop_start = t.get("cop_start", (0, 0))
            position = tuple(cop_start) if isinstance(cop_start, (list, tuple)) else (0, 0)
        else:
            thief_start = t.get("thief_start", (3, 3))
            position = tuple(thief_start) if isinstance(thief_start, (list, tuple)) else (3, 3)

        self.engine = GameEngine(
            board=board,
            role=role,
            position=position,
            max_steps=max_steps,
            survival_threshold=survival_threshold,
            barriers_max=barriers_max,
        )
        self.trail = make_trail(
            board_size,
            model=self.scent_model,
            field_size=int(t.get("smell_grid_size", 5)),
            emit_intensity=float(t.get("emit_intensity", 0.9)),
            decay_per_step=float(t.get("decay_per_step", 0.1)),
            min_center_intensity=float(t.get("min_center_intensity", 0.5)),
        )
        self.opponent_terminal = None
        self.pending_claim = None
        self.pending_claim_position = None
        self.thief_caught = False
        return self.engine

    def apply_move(self, move: str) -> None:
        assert self.engine is not None
        self.engine.apply_own_move(move)

    def observe_barrier_and_claims(self, message: dict) -> None:
        """Absorb an opponent's declared barrier + capture-claim bookkeeping.

        A capture claim is judged against the position that exists RIGHT NOW, at the
        moment it arrives — before this peer's own next move can change it (GAME-009 /
        SEC-007: "move away, then deny" must not be possible). That snapshot rides with
        the claim until it is answered in ``build_result``.
        """
        assert self.engine is not None
        if "barrier_placed" in message:
            self.engine.observe_barrier(message["barrier_placed"])
        if self.engine.role is Role.THIEF and "capture_claim" in message:
            cc = message["capture_claim"]
            self.pending_claim = tuple(cc) if isinstance(cc, list) else cc
            self.pending_claim_position = self.engine.position
        if self.engine.role is Role.POLICE:
            claim_response = message.get("claim_response")
            if claim_response and claim_response.get("caught") is True:
                self.opponent_terminal = Outcome.CAPTURE
            win_claim = message.get("win_claim")
            if win_claim:
                wtype = win_claim.get("type")
                if wtype == "survival":
                    self.opponent_terminal = Outcome.SURVIVAL
                elif wtype == "capture":
                    self.opponent_terminal = Outcome.CAPTURE

    def capture_landed_on_own_cell(self, message: dict) -> bool:
        """True iff this half-turn's incoming capture_claim names our own current cell."""
        assert self.engine is not None
        claim = message.get("capture_claim")
        if claim is None:
            return False
        cell: Any = tuple(claim) if isinstance(claim, list) else claim
        return tuple(cell) == self.engine.position

    def build_result(self, **kwargs: Any) -> dict[str, Any]:
        """Build this turn's ONE sealed payload (see ``wire.sealed_payload``).

        Kept as a method so every existing caller and test keeps its call shape; the
        construction itself lives next to the terminal-final derivation, which must bind
        the same post-move `position` from the same engine state.
        """
        from police_peer.wire.sealed_payload import build_result

        return build_result(self, **kwargs)

    def terminal(self) -> Outcome | None:
        if self.opponent_terminal is not None:
            return self.opponent_terminal
        if self.thief_caught:
            return Outcome.CAPTURE
        if self.engine is not None and self.engine.role is Role.THIEF:
            if self.engine.self_captured():
                return Outcome.CAPTURE
            if self.engine.survived():
                return Outcome.SURVIVAL
        return None
