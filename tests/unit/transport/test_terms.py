"""Tests for terms projection and private config wiring.

TC-25: all 14 keys present, closed, sourced per the PRD §9.2 table.
"""

from __future__ import annotations

from common.transport.terms import TERMS_KEYS, project_terms, terms_diff


class TestTermsKeys:
    """TERMS_KEYS must contain exactly the 14 PRD §9.2 keys."""

    def test_exactly_fourteen_keys(self) -> None:
        assert len(TERMS_KEYS) == 14

    def test_contains_expected_keys(self) -> None:
        expected = {
            "board_size",
            "smell_grid_size",
            "decay_per_step",
            "emit_intensity",
            "min_center_intensity",
            "max_steps",
            "barriers_max",
            "setting",
            "hint_max_words",
            "axis_origin_corner",
            "axis_start_index",
            "thief_start",
            "cop_start",
            "num_games",
        }
        assert expected == TERMS_KEYS

    def test_is_frozenset(self) -> None:
        assert isinstance(TERMS_KEYS, frozenset)


class TestProjectTerms:
    """Tests for project_terms — PRD §9.2 projection table."""

    def _valid_shared(self) -> dict:
        return {
            "board_and_agents": {
                "grid_size": 7,
                "num_agents": 2,
                "thief_start": [3, 3],
                "cop_start": [0, 0],
                "axis_origin_corner": "top-left",
                "axis_start_index": 0,
            },
            "movement_and_barriers": {
                "max_barriers": 14,
                "max_moves": 35,
            },
            "world": {
                "map_area": "New York",
                "hint_max_words": 15,
            },
            "pheromones": {
                "pheromone_center_intensity": 0.9,
                "pheromone_decay": 0.1,
                "pheromone_grid_size": 5,
            },
            "network_and_league": {
                "num_games": 6,
            },
        }

    def test_returns_dict(self) -> None:
        result = project_terms(self._valid_shared(), {})
        assert isinstance(result, dict)

    def test_all_14_keys_present(self) -> None:
        result = project_terms(self._valid_shared(), {})
        assert set(result.keys()) == TERMS_KEYS

    def test_no_extra_keys(self) -> None:
        result = project_terms(self._valid_shared(), {})
        assert set(result.keys()) == TERMS_KEYS

    def test_board_size_from_grid_size(self) -> None:
        result = project_terms(self._valid_shared(), {})
        assert result["board_size"] == 7

    def test_smell_grid_size_fixed_five(self) -> None:
        result = project_terms(self._valid_shared(), {})
        assert result["smell_grid_size"] == 5

    def test_decay_per_step_fixed(self) -> None:
        result = project_terms(self._valid_shared(), {})
        assert result["decay_per_step"] == 0.1

    def test_emit_intensity_fixed(self) -> None:
        result = project_terms(self._valid_shared(), {})
        assert result["emit_intensity"] == 0.9

    def test_min_center_intensity_from_private(self) -> None:
        private = {"min_center_intensity": 0.7}
        result = project_terms(self._valid_shared(), private)
        assert result["min_center_intensity"] == 0.7

    def test_min_center_intensity_default(self) -> None:
        result = project_terms(self._valid_shared(), {})
        assert result["min_center_intensity"] == 0.5

    def test_max_steps_from_max_moves(self) -> None:
        result = project_terms(self._valid_shared(), {})
        assert result["max_steps"] == 35

    def test_barriers_max_from_max_barriers(self) -> None:
        result = project_terms(self._valid_shared(), {})
        assert result["barriers_max"] == 14

    def test_setting_from_map_area(self) -> None:
        result = project_terms(self._valid_shared(), {})
        assert result["setting"] == "New York"

    def test_hint_max_words(self) -> None:
        result = project_terms(self._valid_shared(), {})
        assert result["hint_max_words"] == 15

    def test_axis_origin_corner(self) -> None:
        result = project_terms(self._valid_shared(), {})
        assert result["axis_origin_corner"] == "top-left"

    def test_axis_start_index(self) -> None:
        result = project_terms(self._valid_shared(), {})
        assert result["axis_start_index"] == 0

    def test_thief_start(self) -> None:
        result = project_terms(self._valid_shared(), {})
        assert result["thief_start"] == [3, 3]

    def test_cop_start(self) -> None:
        result = project_terms(self._valid_shared(), {})
        assert result["cop_start"] == [0, 0]

    def test_num_games_default_six(self) -> None:
        result = project_terms(self._valid_shared(), {})
        assert result["num_games"] == 6

    def test_defaults_when_shared_is_empty(self) -> None:
        result = project_terms({}, {})
        assert set(result.keys()) == TERMS_KEYS
        assert result["board_size"] == 7
        assert result["setting"] == "New York"
        assert result["num_games"] == 6

    def test_deterministic(self) -> None:
        shared = self._valid_shared()
        private = {"min_center_intensity": 0.5}
        r1 = project_terms(shared, private)
        r2 = project_terms(shared, private)
        assert r1 == r2


class TestTermsDiff:
    """Tests for terms_diff — detect key disagreement."""

    def test_no_diff_when_identical(self) -> None:
        a = {"board_size": 7, "num_games": 6}
        b = {"board_size": 7, "num_games": 6}
        assert terms_diff(a, b) == []

    def test_detects_missing_key(self) -> None:
        a = {"board_size": 7}
        b = {"board_size": 7, "num_games": 6}
        assert terms_diff(a, b) == ["num_games"]

    def test_detects_extra_key(self) -> None:
        a = {"board_size": 7, "num_games": 6}
        b = {"board_size": 7}
        assert terms_diff(a, b) == ["num_games"]

    def test_detects_value_mismatch(self) -> None:
        a = {"board_size": 7}
        b = {"board_size": 9}
        assert terms_diff(a, b) == ["board_size"]

    def test_sorted_results(self) -> None:
        a = {"z": 1, "a": 2}
        b = {"z": 1, "a": 3}
        assert terms_diff(a, b) == ["a"]

    def test_empty_dicts(self) -> None:
        assert terms_diff({}, {}) == []
