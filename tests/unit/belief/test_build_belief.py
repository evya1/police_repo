"""build_belief factory tests."""

from __future__ import annotations

import pytest

from common.domain.board import Board
from police_peer.belief import build_belief


def test_default_config() -> None:
    bg = build_belief(Board(size=7), {"belief": {}}, probe=None)
    assert bg.prob((0, 0)) == pytest.approx(1.0 / 49.0)


def test_custom_trust() -> None:
    bg = build_belief(Board(size=7), {"belief": {"smell_trust_weight": 2.0}}, probe=None)
    assert bg._trust == 2.0


def test_unknown_update_form_raises() -> None:
    with pytest.raises(ValueError, match="unknown update_form"):
        build_belief(Board(size=7), {"belief": {"update_form": "invalid"}}, probe=None)


def test_kernel_requires_probe() -> None:
    with pytest.raises(ValueError, match="kernel_bayes_v1 requires an EmissionProbe"):
        build_belief(Board(size=7), {"belief": {"update_form": "kernel_bayes_v1"}}, probe=None)
