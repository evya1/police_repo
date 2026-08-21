"""Differential test against the reference worked example.

Covers TC-B06: reference E1 with trust_v1.
"""

from __future__ import annotations

import pytest

from common.domain.board import Board
from police_peer.belief import build_belief
from police_peer.scent.profiles.subtractive_chebyshev_v1 import smell_emit


def test_reference_worked_example() -> None:
    """TC-B06: reference E1 transcript, trust_v1, peak (4,3), centre mass ≈ 0.0505."""
    board = Board(size=7)
    cfg = {"belief": {"update_form": "trust_v1", "smell_trust_weight": 4.0}}
    bg = build_belief(board, cfg, probe=None)

    field = smell_emit((4, 3), 0.9, 5, 7)
    bg.observe_smell(field)

    assert bg.most_likely() == (4, 3)
    centre_mass = bg.prob((4, 3))
    assert centre_mass == pytest.approx(0.0505, abs=1e-4)
