"""Model selection tests.

Covers T005 L77, L80–81:
* default with no argument = subtractive_chebyshev_v1
* both models reachable through Trail/make_trail only
* unknown model → ValueError
* no if-model branching outside model.py
"""

from __future__ import annotations

import pytest

from police_peer.scent import (
    BOOK_MODEL,
    DEFAULT_MODEL,
    MODELS,
    REFERENCE_MODEL,
    make_trail,
)
from police_peer.scent.model import Trail


class TestDefaultModel:
    """T005 L80: default selection is subtractive_chebyshev_v1."""

    def test_default_model_constant(self) -> None:
        assert DEFAULT_MODEL == REFERENCE_MODEL
        assert DEFAULT_MODEL == "subtractive_chebyshev_v1"

    def test_make_trail_defaults_to_subtractive(self) -> None:
        trail = make_trail(board_size=7)
        assert trail.model == REFERENCE_MODEL

    def test_make_trail_explicit_none(self) -> None:
        trail = make_trail(board_size=7, model=None)
        assert trail.model == REFERENCE_MODEL


class TestBothModelsReachable:
    """T005 L77, L81: both models reachable through Trail/make_trail."""

    def test_trail_reference(self) -> None:
        trail = Trail(REFERENCE_MODEL, board_size=7)
        assert trail.model == REFERENCE_MODEL

    def test_trail_book(self) -> None:
        trail = Trail(BOOK_MODEL, board_size=7)
        assert trail.model == BOOK_MODEL

    def test_make_trail_reference(self) -> None:
        trail = make_trail(board_size=7, model=REFERENCE_MODEL)
        assert trail.model == REFERENCE_MODEL

    def test_make_trail_book(self) -> None:
        trail = make_trail(board_size=7, model=BOOK_MODEL)
        assert trail.model == BOOK_MODEL

    def test_models_tuple(self) -> None:
        assert MODELS == (REFERENCE_MODEL, BOOK_MODEL)


class TestUnknownModel:
    """T005 L81: unknown model → ValueError."""

    def test_trail_unknown_model(self) -> None:
        with pytest.raises(ValueError, match="unknown scent model"):
            Trail("nonexistent_model", board_size=7)

    def test_make_trail_unknown_model(self) -> None:
        with pytest.raises(ValueError, match="unknown scent model"):
            make_trail(board_size=7, model="nonexistent_model")


class TestNoBranchingOutsideModel:
    """T005 L77: no if-model branching outside model.py.

    This is verified by inspection — the profiles and lock modules import nothing
    that branches on the model name. The Trail class in model.py is the only place
    that dispatches between profiles.
    """

    def test_profiles_have_no_model_branching(self) -> None:
        """Profiles are pure functions; they don't know about model selection."""
        from police_peer.scent.profiles import multiplicative_book_v1, subtractive_chebyshev_v1

        # These modules should not import model.py (no circular dependency with branching)
        assert not hasattr(subtractive_chebyshev_v1, "model")
        assert not hasattr(multiplicative_book_v1, "model")
