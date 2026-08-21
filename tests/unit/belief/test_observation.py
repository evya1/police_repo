"""Scent observation tests: trust_v1 and kernel_bayes_v1.

Covers TC-B05, TC-B07, TC-B08.
"""

from __future__ import annotations

import pytest

from common.domain.board import Board
from police_peer.belief import build_belief
from police_peer.belief.grid import BeliefGrid


def _board(size: int = 7) -> Board:
    return Board(size=size)


def _belief(size: int = 7, update_form: str = "trust_v1", **kwargs) -> BeliefGrid:
    cfg = {"belief": {"update_form": update_form, **kwargs}}
    return build_belief(_board(size), cfg, probe=None)


class TestObserveTrustV1:
    """TC-B05: trust_v1 observation updates probabilities correctly."""

    def test_single_cell_boost(self) -> None:
        bg = _belief()
        bg.observe_smell({"3,3": 0.7})
        assert bg.prob((3, 3)) > bg.prob((0, 0))

    def test_sum_remains_one(self) -> None:
        bg = _belief()
        bg.observe_smell({"3,3": 0.7})
        total = sum(bg.prob((r, c)) for r in range(7) for c in range(7))
        assert total == pytest.approx(1.0)

    def test_out_of_bounds_ignored(self) -> None:
        bg = _belief()
        bg.observe_smell({"99,99": 0.9})
        total = sum(bg.prob((r, c)) for r in range(7) for c in range(7))
        assert total == pytest.approx(1.0)

    def test_empty_field_no_change(self) -> None:
        bg = _belief()
        before = bg.as_matrix()
        bg.observe_smell({})
        assert bg.as_matrix() == before


class TestObserveKernel:
    """TC-B07: kernel_bayes_v1 observation with field and empty field."""

    def test_field_centred_at_peak(self) -> None:
        """Field centred at (4,3) => peak at (4,3)."""
        class DummyProbe:
            def field_at(self, center):
                return {f"{center[0]},{center[1]}": 0.9}

        cfg = {"belief": {"update_form": "kernel_bayes_v1", "smell_trust_weight": 4.0}}
        bg = build_belief(_board(7), cfg, probe=DummyProbe())
        bg.observe_smell({"4,3": 0.9})
        assert bg.most_likely() == (4, 3)

    def test_empty_field_negative_evidence(self) -> None:
        """Empty field after diffusion => peak mass strictly below pre-observation peak."""
        class DummyProbe:
            def field_at(self, center):
                return {f"{center[0]},{center[1]}": 0.9}

        cfg = {"belief": {"update_form": "kernel_bayes_v1", "smell_trust_weight": 4.0}}
        bg = build_belief(_board(7), cfg, probe=DummyProbe())

        bg.observe_smell({"4,3": 0.9})
        peak_before = bg.peak_probability()

        bg.diffuse()
        bg.observe_smell({})
        peak_after = bg.peak_probability()

        assert peak_after < peak_before


class TestKernelProbeSeam:
    """TC-B08: kernel_bayes_v1 reads through the seam; no profile imports in belief/."""

    def test_different_probes_give_different_results(self) -> None:
        """Monkeypatched probe gives different probabilities."""
        class ProbeA:
            def field_at(self, center):
                return {f"{center[0]},{center[1]}": 0.9}

        class ProbeB:
            def field_at(self, center):
                return {f"{center[0]},{center[1]}": 0.5}

        cfg = {"belief": {"update_form": "kernel_bayes_v1", "smell_trust_weight": 4.0}}
        bg_a = build_belief(_board(7), cfg, probe=ProbeA())
        bg_b = build_belief(_board(7), cfg, probe=ProbeB())

        bg_a.observe_smell({"4,3": 0.9})
        bg_b.observe_smell({"4,3": 0.9})

        assert bg_a.prob((4, 3)) != bg_b.prob((4, 3))

    def test_no_profile_imports_in_belief_module(self) -> None:
        """belief/ should not import any scent profile modules directly."""
        import police_peer.belief as belief_pkg
        import police_peer.belief.grid as grid_mod
        import police_peer.belief.hints as hints_mod
        import police_peer.belief.probe as probe_mod
        import police_peer.belief.update as update_mod

        for mod in (grid_mod, update_mod, probe_mod, hints_mod, belief_pkg):
            imported_modules = set()
            for name in dir(mod):
                obj = getattr(mod, name)
                if hasattr(obj, "__module__"):
                    imported_modules.add(obj.__module__)
            for imp in imported_modules:
                assert "scent.profiles" not in imp, (
                    f"{mod.__name__} imports scent.profiles via {imp}"
                )
                assert "strategy" not in imp, f"{mod.__name__} imports strategy via {imp}"
                assert "transport" not in imp, f"{mod.__name__} imports transport via {imp}"
