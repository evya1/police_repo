"""Config validation for the distributed Police/Thief game.

Loads and validates `config/game.json` against the Appendix B section structure
and Appendix F binding values. Fixed values are immutable; minimums may be
raised by agreement but never lowered; negotiated fields use defaults when
absent.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ConfigError(Exception):
    """Raised when configuration is invalid."""


class FixedValueError(ConfigError):
    """A fixed value was changed."""


class MinimumError(ConfigError):
    """A minimum value was lowered."""


class FieldError(ConfigError):
    """A required field is missing or renamed."""


# Fixed (immutable) values from App. F
_FIXED_MOVE_SET = frozenset({"N", "S", "E", "W", "STAY"})

_FIXED_SCORING = {
    "capture_cop": 20,
    "capture_thief": 5,
    "survival_cop": 5,
    "survival_thief": 10,
    "tie_score": 2,
    "technical_loss": 0,
}

# Minimum values from App. F
_MINIMUMS = {
    "grid_size": 7,
    "max_barriers": 14,
    "max_moves": 35,
    "survival_threshold": 35,
}

# Required sections (App. B)
_REQUIRED_SECTIONS = frozenset(
    {
        "schema_version",
        "agreed_between",
        "board_and_agents",
        "movement_and_barriers",
        "scoring",
        "world",
        "pheromones",
        "network_and_league",
        "rate_limiter_gatekeeper",
    }
)

# Required fields per section (App. B)
_REQUIRED_FIELDS: dict[str, frozenset[str]] = {
    "board_and_agents": frozenset(
        {
            "grid_size",
            "num_agents",
            "thief_start",
            "cop_start",
            "axis_origin_corner",
            "axis_start_index",
        }
    ),
    "movement_and_barriers": frozenset(
        {
            "move_set",
            "max_barriers",
            "max_moves",
            "survival_threshold",
        }
    ),
    "scoring": frozenset(
        {
            "capture_cop",
            "capture_thief",
            "survival_cop",
            "survival_thief",
            "tie_score",
            "technical_loss",
        }
    ),
    "world": frozenset({"map_area", "hint_max_words"}),
    "pheromones": frozenset(
        {
            "pheromone_center_intensity",
            "pheromone_decay",
            "pheromone_grid_size",
        }
    ),
    "network_and_league": frozenset(
        {
            "response_timeout_sec",
            "watchdog_timeout_sec",
            "num_games",
            "diversity_reward",
            "min_games_to_pass",
            "max_games_per_team",
            "token_budget_per_series",
        }
    ),
    "rate_limiter_gatekeeper": frozenset(
        {
            "requests_per_minute",
            "concurrent_requests",
            "retry_backoff_sec",
            "max_retries",
            "queue_depth",
        }
    ),
}


def load_config(path: Path | str) -> dict[str, Any]:
    """Load and validate game.json from the given path.

    Args:
        path: Path to game.json.

    Returns:
        Validated config dict.

    Raises:
        ConfigError: If the config is invalid.
    """
    path = Path(path)
    if not path.is_file():
        raise ConfigError(f"Config file not found: {path}")

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    validate_config(data)
    return data


def validate_config(data: dict[str, Any]) -> None:
    """Validate a config dict against the binding rules.

    Args:
        data: Parsed game.json contents.

    Raises:
        ConfigError: If validation fails.
    """
    _validate_sections(data)
    _validate_fields(data)
    _validate_fixed_values(data)
    _validate_minimums(data)
    _validate_num_agents(data)


def _validate_sections(data: dict[str, Any]) -> None:
    """All required sections must be present (CFG-004)."""
    missing = _REQUIRED_SECTIONS - set(data.keys())
    if missing:
        raise FieldError(f"Missing required sections: {', '.join(sorted(missing))}")

    unknown = set(data.keys()) - _REQUIRED_SECTIONS
    if unknown:
        raise FieldError(f"Unknown sections: {', '.join(sorted(unknown))}")


def _validate_fields(data: dict[str, Any]) -> None:
    """All required fields must be present in their sections."""
    for section, fields in _REQUIRED_FIELDS.items():
        section_data = data.get(section, {})
        missing = fields - set(section_data.keys())
        if missing:
            raise FieldError(f"Missing required field '{section}.{', '.join(sorted(missing))}'")

        unknown = set(section_data.keys()) - fields
        if unknown:
            raise FieldError(f"Unknown field in '{section}': {', '.join(sorted(unknown))}")


def _validate_fixed_values(data: dict[str, Any]) -> None:
    """Fixed values must match exactly."""
    movement = data.get("movement_and_barriers", {})
    if set(movement.get("move_set", [])) != _FIXED_MOVE_SET:
        raise FixedValueError("move_set is fixed and must be exactly N, S, E, W, STAY")

    scoring = data.get("scoring", {})
    for key, expected in _FIXED_SCORING.items():
        actual = scoring.get(key)
        if actual != expected:
            raise FixedValueError(f"scoring.{key} is fixed at {expected}, got {actual}")


def _validate_minimums(data: dict[str, Any]) -> None:
    """Minimum values must not fall below threshold."""
    board = data.get("board_and_agents", {})
    grid_size = board.get("grid_size")
    if grid_size < _MINIMUMS["grid_size"]:
        raise MinimumError(f"grid_size must be >= {_MINIMUMS['grid_size']}, got {grid_size}")

    movement = data.get("movement_and_barriers", {})
    for key, minimum in _MINIMUMS.items():
        value = movement.get(key)
        if value is not None and value < minimum:
            raise MinimumError(f"{key} must be >= {minimum}, got {value}")


def _validate_num_agents(data: dict[str, Any]) -> None:
    """Number of agents must be exactly 2 (GAME-002)."""
    board = data.get("board_and_agents", {})
    num_agents = board.get("num_agents")
    if num_agents != 2:
        raise ConfigError(f"num_agents must be exactly 2, got {num_agents}")


def overlay_toml(json_path: Path | str, toml_path: Path | str) -> dict[str, Any]:
    """Load JSON config and overlay TOML local settings.

    The JSON value wins on conflicts; TOML can add local-only settings but
    must not weaken signed conditions.

    Args:
        json_path: Path to game.json.
        toml_path: Path to game.toml.

    Returns:
        Merged config dict.
    """
    import tomllib  # Python 3.11+

    data = load_config(json_path)

    toml_path = Path(toml_path)
    if toml_path.is_file():
        with open(toml_path, "rb") as f:
            toml_data = tomllib.load(f)
        _overlay_toml(data, toml_data)

    return data


def _overlay_toml(base: dict[str, Any], toml: dict[str, Any]) -> None:
    """Recursively overlay TOML values onto base dict.

    JSON values take precedence on conflicts. TOML may add new keys but
    must not weaken existing signed values.
    """
    for key, value in toml.items():
        if key in base and isinstance(value, dict) and isinstance(base[key], dict):
            _overlay_toml(base[key], value)
            # JSON wins on scalar conflicts — do not overwrite
