"""Kernel probe tests: EmissionProbe seam and kernel_factors.

Covers TC-B08.
"""

from __future__ import annotations

import pytest

from common.domain.board import Board
from police_peer.belief import build_belief
from police_peer.belief.probe import kernel_factors


class DummyProbe:
    """Simple probe for testing: emits a point mass at center."""

    def field_at(self, center):
        return {f"{center[0]},{center[1]}": 0.9}


class TestEmissionProbe:
    """EmissionProbe Protocol and kernel_factors."""

    def test_kernel_factors_empty_field(self) -> None:
        factors = kernel_factors(7, {}, DummyProbe(), 4.0)
        for row in factors:
            for f in row:
                assert f == pytest.approx(1.0 - 4.0)

    def test_kernel_factors_with_field(self) -> None:
        factors = kernel_factors(7, {"3,3": 0.9}, DummyProbe(), 4.0)
        assert factors[3][3] == pytest.approx(3.0)
        assert factors[0][0] == pytest.approx(-1.0)

    def test_kernel_factors_different_field(self) -> None:
        factors1 = kernel_factors(7, {"3,3": 0.9}, DummyProbe(), 4.0)
        factors2 = kernel_factors(7, {"3,3": 0.5}, DummyProbe(), 4.0)
        assert factors1[3][3] != factors2[3][3]


class TestKernelBelief:
    """kernel_bayes_v1 belief board with probe."""

    def test_kernel_bayes_requires_probe(self) -> None:
        with pytest.raises(ValueError, match="kernel_bayes_v1 requires an EmissionProbe"):
            build_belief(
                Board(size=7),
                {"belief": {"update_form": "kernel_bayes_v1"}},
                probe=None,
            )

    def test_kernel_bayes_peak_at_field_center(self) -> None:
        bg = build_belief(
            Board(size=7),
            {"belief": {"update_form": "kernel_bayes_v1", "smell_trust_weight": 4.0}},
            probe=DummyProbe(),
        )
        bg.observe_smell({"3,3": 0.9})
        assert bg.most_likely() == (3, 3)

    def test_kernel_bayes_empty_field_reduces_mass(self) -> None:
        bg = build_belief(
            Board(size=7),
            {"belief": {"update_form": "kernel_bayes_v1", "smell_trust_weight": 4.0}},
            probe=DummyProbe(),
        )
        bg.observe_smell({"3,3": 0.9})
        peak_before = bg.peak_probability()
        bg.diffuse()
        bg.observe_smell({})
        peak_after = bg.peak_probability()
        assert peak_after < peak_before

    def test_kernel_bayes_different_probe_different_result(self) -> None:
        class ProbeA:
            def field_at(self, center):
                return {f"{center[0]},{center[1]}": 0.9}

        class ProbeB:
            def field_at(self, center):
                return {f"{center[0]},{center[1]}": 0.3}

        cfg = {"belief": {"update_form": "kernel_bayes_v1", "smell_trust_weight": 4.0}}
        bg_a = build_belief(Board(size=7), cfg, probe=ProbeA())
        bg_b = build_belief(Board(size=7), cfg, probe=ProbeB())

        bg_a.observe_smell({"3,3": 0.9})
        bg_b.observe_smell({"3,3": 0.9})

        assert bg_a.prob((3, 3)) != bg_b.prob((3, 3))
