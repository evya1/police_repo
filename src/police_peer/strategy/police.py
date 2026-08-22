"""PoliceBrain — scored pursuit + barrier-first policy.

The M-03 pursuit policy: barrier first via where_place_barrier (FR-P2),
then the two-key pursuit scan over the CT-01 legal list (FR-P3; derived
design — PLANQ-008 records the approved priorities).
"""

from __future__ import annotations

from common.domain.board import Board, Cell, manhattan
from common.domain.scoring import Role

from .barriers import where_place_barrier
from .base import BrainBase


class PoliceBrain(BrainBase):
    """The M-03 pursuit policy: barrier first via where_place_barrier (FR-P2),
    then the two-key pursuit scan over the CT-01 legal list (FR-P3; derived
    design — PLANQ-008 records the approved priorities).
    """

    def __init__(
        self,
        *,
        min_confidence: float = 0.10,
        barrier_mass_floor: float = 0.05,
        w_mass: float = 1.0,
        w_cut: float = 0.5,
        route_slack: int = 1,
        barrier_reserve: int = 3,
        strong_threshold: float = 0.8,
        barrier_score_threshold: float = 0.3,
        **base,
    ) -> None:
        super().__init__(**base)
        self.min_confidence = min_confidence
        self.barrier_mass_floor = barrier_mass_floor
        self.w_mass = w_mass
        self.w_cut = w_cut
        self.route_slack = route_slack
        self.barrier_reserve = barrier_reserve
        self.strong_threshold = strong_threshold
        self.barrier_score_threshold = barrier_score_threshold
        self.role = Role.POLICE
        self._cfg: dict[str, object] = {
            "barrier_mass_floor": barrier_mass_floor,
            "w_mass": w_mass,
            "w_cut": w_cut,
            "route_slack": route_slack,
            "barrier_reserve": barrier_reserve,
            "strong_threshold": strong_threshold,
            "barrier_score_threshold": barrier_score_threshold,
        }

    def _target(self, state, belief) -> Cell:
        """FR-P3, fixed order: belief.most_likely() when
        belief.peak_probability() >= min_confidence; else
        scent.hottest(self.last_field); else the board centre.
        """
        from police_peer.scent.model import hottest

        if belief.peak_probability() >= self.min_confidence:
            return belief.most_likely()
        hot = hottest(self.last_field)
        if hot is not None:
            return hot
        # Board centre: (size // 2, size // 2).
        size = state.board.size
        return (size // 2, size // 2)

    def _decide_move(
        self, state, belief
    ) -> tuple[str, Cell | None]:
        """Barrier first (FR-P2/FR-P4), then pursuit (FR-P3):

        target_cell = where_place_barrier(state, belief, self._cfg)
        if target_cell is not None:
            return "STAY", target_cell        # move forfeit (GAME-006)
        # pursuit scan:
        threat = self._target(state, belief)
        for action in state.legal_moves():    # CT-01 order: N, S, W, E, STAY
            dest = state.board.step(state.position, action)   # STAY -> position
            key  = (manhattan(dest, threat), -belief.prob(dest))
            # FIRST strict minimum in CT-01 order — deterministic tie-break
        Returns (action, None)
        """
        # Barrier first (FR-P2/FR-P4).
        target_cell = where_place_barrier(state, belief, self._cfg)
        if target_cell is not None:
            return "STAY", target_cell

        # Pursuit scan (FR-P3).
        threat = self._target(state, belief)
        board: Board = state.board
        position = state.position

        legal = state.legal_moves()
        best_action = legal[0]
        best_key = (
            manhattan(board.step(position, legal[0]) if legal[0] != "STAY" else position, threat),
            -belief.prob(position if legal[0] == "STAY" else board.step(position, legal[0])),
        )

        for action in legal:
            dest = board.step(position, action) if action != "STAY" else position
            key = (manhattan(dest, threat), -belief.prob(dest))
            if key < best_key:
                best_key = key
                best_action = action

        return best_action, None
