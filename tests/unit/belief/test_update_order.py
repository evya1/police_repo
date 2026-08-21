"""Half-turn update order tests: apply_half_turn follows the pinned sequence.

Covers the SD-B2 invariant: exclude -> diffuse -> observe -> hint -> self-exclude.
"""

from __future__ import annotations

import pytest

from common.domain.board import Board
from police_peer.belief import build_belief
from police_peer.belief.grid import BeliefGrid
from police_peer.belief.update import apply_half_turn


def _belief(**kwargs) -> BeliefGrid:
    cfg = {"belief": kwargs}
    return build_belief(Board(size=7), cfg, probe=None)


class TestHalfTurnOrder:
    """apply_half_turn follows the fixed update order."""

    def test_barrier_excluded_before_diffuse(self) -> None:
        """Barrier exclusion happens before diffusion, so barrier mass doesn't leak back."""
        bg = _belief()
        apply_half_turn(
            bg,
            barrier=(3, 3),
            field={},
            hint="",
            arena="New York",
            own_cell=(0, 0),
            capture_landed=True,
        )
        assert bg.prob((3, 3)) == pytest.approx(0.0)

    def test_own_cell_excluded_when_no_capture(self) -> None:
        bg = _belief()
        apply_half_turn(
            bg,
            barrier=None,
            field={},
            hint="",
            arena="New York",
            own_cell=(3, 3),
            capture_landed=False,
        )
        assert bg.prob((3, 3)) == pytest.approx(0.0)

    def test_own_cell_kept_when_capture_landed(self) -> None:
        bg = _belief()
        apply_half_turn(
            bg,
            barrier=None,
            field={},
            hint="",
            arena="New York",
            own_cell=(3, 3),
            capture_landed=True,
        )
        assert bg.prob((3, 3)) > 0.0

    def test_sum_is_one_after_half_turn(self) -> None:
        bg = _belief()
        apply_half_turn(
            bg,
            barrier=(1, 1),
            field={"3,3": 0.5},
            hint="near Times Square",
            arena="New York",
            own_cell=(0, 0),
            capture_landed=False,
        )
        total = sum(sum(row) for row in bg._matrix)
        assert total == pytest.approx(1.0)

    def test_barrier_and_own_cell_both_excluded(self) -> None:
        """When barrier != own_cell, both are excluded."""
        bg = _belief()
        apply_half_turn(
            bg,
            barrier=(2, 2),
            field={},
            hint="",
            arena="New York",
            own_cell=(3, 3),
            capture_landed=False,
        )
        assert bg.prob((2, 2)) == pytest.approx(0.0)
        assert bg.prob((3, 3)) == pytest.approx(0.0)

    def test_barrier_equals_own_cell(self) -> None:
        """When barrier == own_cell, exclusion composes (still zero)."""
        bg = _belief()
        apply_half_turn(
            bg,
            barrier=(3, 3),
            field={},
            hint="",
            arena="New York",
            own_cell=(3, 3),
            capture_landed=False,
        )
        assert bg.prob((3, 3)) == pytest.approx(0.0)

    def test_diffuse_spreads_mass(self) -> None:
        """Diffusion spreads mass from high-probability cells."""
        bg = _belief()
        bg._matrix[0][0] = 1.0
        bg._normalize()
        apply_half_turn(
            bg,
            barrier=None,
            field={},
            hint="",
            arena="New York",
            own_cell=(0, 0),
            capture_landed=True,
        )
        assert bg.prob((0, 0)) < 1.0
        assert bg.prob((0, 1)) > 0.0
        assert bg.prob((1, 0)) > 0.0

    def test_observation_updates_mass(self) -> None:
        """Observation changes probability distribution."""
        bg = _belief()
        apply_half_turn(
            bg,
            barrier=None,
            field={"3,3": 0.9},
            hint="",
            arena="New York",
            own_cell=(0, 0),
            capture_landed=True,
        )
        assert bg.prob((3, 3)) > bg.prob((0, 0))

    def test_hint_changes_distribution(self) -> None:
        """Hint changes probability distribution."""
        bg = _belief()
        apply_half_turn(
            bg,
            barrier=None,
            field={},
            hint="near Times Square",
            arena="New York",
            own_cell=(0, 0),
            capture_landed=True,
        )
        ts_cells = [(3, 3), (3, 4), (4, 3)]
        for cell in ts_cells:
            assert bg.prob(cell) > bg.prob((0, 0))
