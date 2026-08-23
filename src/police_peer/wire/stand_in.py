"""StandInEngine — the baseline TurnEngine adapter (documented legacy path).

Composes a ``SubgameSession``; does not subclass and is not subclassed by
``BrainDrivenEngine`` (both adapters compose the shared session instead).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from common.domain.scoring import Outcome, Role
from police_peer.wire.sealed_payload import build_terminal_final
from police_peer.wire.session import SubgameSession


@dataclass
class StandInEngine:
    """A stateful TurnEngine using GameEngine for the series (baseline behaviour)."""

    natural_role: Role
    board_size: int = 7
    seed: int = 0
    terms: dict | None = None
    strategy: Any = None

    _session: SubgameSession | None = None

    def start_subgame(self, sub_game: int, role: Role, terms: dict | None = None) -> None:
        """Create a fresh session (GameEngine + own trail) for the given sub-game."""
        t = terms or self.terms or {}
        self._session = SubgameSession(natural_role=self.natural_role, board_size=self.board_size, seed=self.seed)
        self._session.start(sub_game, role, terms=t)

    def decide(self) -> dict:
        """Return a move dict for the current sub-game and role."""
        if self._session is None or self._session.engine is None:
            raise RuntimeError("start_subgame must be called before decide")
        engine = self._session.engine

        legal_moves = engine.legal_moves()
        if self.strategy is not None and hasattr(self.strategy, "select_action"):
            view = {
                "role": engine.role.value,
                "position": list(engine.position),
                "step": engine.step,
                "barriers": [list(b) for b in engine.barriers],
            }
            move = self.strategy.select_action(legal_moves, view)
            if move not in legal_moves:
                move = legal_moves[0] if legal_moves else "STAY"
        else:
            move = legal_moves[0] if legal_moves else "STAY"

        self._session.apply_move(move)
        return self._session.build_result(move=move, hint="I am here")

    def observe_opponent(self, message: dict) -> None:
        """Absorb an opponent's turn message (barrier + claim bookkeeping only)."""
        if self._session is None or self._session.engine is None:
            return
        self._session.observe_barrier_and_claims(message)

    def terminal(self) -> Outcome | None:
        if self._session is None:
            return None
        return self._session.terminal()

    def terminal_final(self) -> dict | None:
        """The sealed game-ending final step owed after settling, or None.

        One derivation, shared with the other wire adapter (T054).
        """
        if self._session is None:
            return None
        return build_terminal_final(self._session)
