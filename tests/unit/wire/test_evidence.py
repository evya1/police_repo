"""Wire-boundary scent evidence normalization tests (H3, Phase 6)."""

from __future__ import annotations

import math

from common.domain.board import Board
from police_peer.wire.evidence import normalize_scent_field


class TestNormalizeScentField:
    def test_valid_field_passes_through(self) -> None:
        board = Board(size=7)
        raw = {"1,2": 0.5, "3,3": 0.9}
        clean = normalize_scent_field(raw, board)
        assert clean == {"1,2": 0.5, "3,3": 0.9}

    def test_non_mapping_returns_empty(self) -> None:
        board = Board(size=7)
        assert normalize_scent_field(None, board) == {}
        assert normalize_scent_field("not a dict", board) == {}
        assert normalize_scent_field([1, 2, 3], board) == {}

    def test_malformed_keys_are_discarded(self) -> None:
        board = Board(size=7)
        raw = {"bogus": 0.5, "1": 0.5, "1,2,3": 0.5, "a,b": 0.5, "1,2": 0.4}
        assert normalize_scent_field(raw, board) == {"1,2": 0.4}

    def test_out_of_board_coordinates_discarded(self) -> None:
        board = Board(size=7)
        raw = {"7,0": 0.5, "-1,0": 0.5, "6,6": 0.3}
        assert normalize_scent_field(raw, board) == {"6,6": 0.3}

    def test_boolean_intensity_rejected(self) -> None:
        board = Board(size=7)
        raw = {"1,1": True, "2,2": 0.5}
        assert normalize_scent_field(raw, board) == {"2,2": 0.5}

    def test_non_numeric_intensity_rejected(self) -> None:
        board = Board(size=7)
        raw = {"1,1": "0.9", "2,2": 0.5}
        assert normalize_scent_field(raw, board) == {"2,2": 0.5}

    def test_nan_and_infinite_rejected(self) -> None:
        board = Board(size=7)
        raw = {"1,1": float("nan"), "2,2": float("inf"), "3,3": float("-inf"), "4,4": 0.2}
        assert normalize_scent_field(raw, board) == {"4,4": 0.2}

    def test_negative_intensity_rejected(self) -> None:
        board = Board(size=7)
        raw = {"1,1": -0.5, "2,2": 0.5}
        assert normalize_scent_field(raw, board) == {"2,2": 0.5}

    def test_returns_fresh_dict_not_caller_object(self) -> None:
        board = Board(size=7)
        raw = {"1,1": 0.5}
        clean = normalize_scent_field(raw, board)
        clean["9,9"] = 1.0
        assert "9,9" not in raw

    def test_never_raises_on_hostile_input(self) -> None:
        board = Board(size=7)
        hostile_inputs = [
            {"1,1": object()},
            {123: 0.5},
            {"": 0.5},
            {",": 0.5},
            {"1,": 0.5},
            {",1": 0.5},
        ]
        for raw in hostile_inputs:
            result = normalize_scent_field(raw, board)  # must never raise
            assert isinstance(result, dict)


class TestHottestTotality:
    """hottest() is total: a malformed field must never crash a game (H3 defense in
    depth, on top of the wire-boundary normalization above)."""

    def test_empty_field_returns_none(self) -> None:
        from police_peer.scent.model import hottest

        assert hottest({}) is None

    def test_malformed_keys_never_raise(self) -> None:
        from police_peer.scent.model import hottest

        field = {
            "bogus": 0.9,
            "1": 0.9,
            "1,2,3": 0.9,
            "a,b": 0.9,
            "": 0.9,
            "1,2": 0.5,
        }
        assert hottest(field) == (1, 2)

    def test_nan_inf_and_bool_values_never_raise(self) -> None:
        from police_peer.scent.model import hottest

        field = {
            "0,0": float("nan"),
            "1,1": float("inf"),
            "2,2": True,
            "3,3": "not a number",
            "4,4": 0.3,
        }
        assert hottest(field) == (4, 4)

    def test_all_malformed_returns_none_not_crash(self) -> None:
        from police_peer.scent.model import hottest

        assert hottest({"x": "y", "z": None}) is None
        assert not math.isnan(0.0)  # sanity: math import used
