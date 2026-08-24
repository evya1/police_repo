"""Private per-group TOML sections (App. B §4): all optional, safe defaults, JSON always wins."""

from __future__ import annotations

import json
from pathlib import Path

from common.config import (
    DEFAULT_EMAIL_MODE,
    DEFAULT_REPORT_RECIPIENT,
    PrivateConfig,
    load_private,
    overlay_toml,
)


def test_a_missing_private_file_yields_all_defaults(tmp_path: Path) -> None:
    private = load_private(tmp_path / "does-not-exist.toml")

    assert private == PrivateConfig()
    assert private.email_recipient == DEFAULT_REPORT_RECIPIENT
    assert private.email_mode == DEFAULT_EMAIL_MODE
    assert private.members == ()
    assert private.repos == {}


def test_every_section_parses(tmp_path: Path) -> None:
    toml_path = tmp_path / "game.toml"
    toml_path.write_text(
        """
        [game]
        group_name = "Team A"
        group_id = "team-a"
        members = ["Alice", "Bob"]
        sub_game_number = 3

        [game.repos]
        cop = "https://github.com/team-a/cop"
        thief = "https://github.com/team-a/thief"

        [network]
        my_port = 8101
        opponent_url = "http://127.0.0.1:8102/mcp"
        turn_timeout_seconds = 45.0

        [llm]
        model = "gpt-x"
        step_deadline_seconds = 12.5

        [email]
        recipient = "someone@example.com"
        mode = "send"

        [strategy]
        thief_class = "aggressive"
        police_class = "cautious"

        [trash_talk]
        provider = "template"
        """,
        encoding="utf-8",
    )

    private = load_private(toml_path)

    assert private.group_name == "Team A"
    assert private.group_id == "team-a"
    assert private.members == ("Alice", "Bob")
    assert private.sub_game_number == 3
    assert private.repos == {
        "cop": "https://github.com/team-a/cop",
        "thief": "https://github.com/team-a/thief",
    }
    assert private.my_port == 8101
    assert private.opponent_url == "http://127.0.0.1:8102/mcp"
    assert private.turn_timeout_seconds == 45.0
    assert private.llm_model == "gpt-x"
    assert private.step_deadline_seconds == 12.5
    assert private.email_recipient == "someone@example.com"
    assert private.email_mode == "send"
    assert private.thief_class == "aggressive"
    assert private.police_class == "cautious"
    assert private.trash_talk_provider == "template"


def test_email_defaults_are_exactly_the_two_pinned_values(tmp_path: Path) -> None:
    toml_path = tmp_path / "game.toml"
    toml_path.write_text("[game]\ngroup_id = \"x\"\n", encoding="utf-8")

    private = load_private(toml_path)

    assert private.email_recipient == "rmisegal+uoh26finalgame@gmail.com"
    assert private.email_mode == "dry-run"


def test_the_example_toml_parses_and_carries_the_new_sections() -> None:
    example = Path(__file__).resolve().parents[2] / "config" / "game.toml.example"

    private = load_private(example)

    assert private.email_recipient == "rmisegal+uoh26finalgame@gmail.com"
    assert private.email_mode == "dry-run"
    assert private.repos


def test_a_shared_json_key_beats_a_private_toml_key_of_the_same_name(tmp_path: Path) -> None:
    """overlay_toml: the private file may never weaken a signed shared term."""
    json_path = tmp_path / "game.json"
    json_path.write_text(
        json.dumps(
            {
                "schema_version": "1",
                "agreed_between": [],
                "board_and_agents": {
                    "grid_size": 7,
                    "num_agents": 2,
                    "thief_start": [3, 3],
                    "cop_start": [0, 0],
                    "axis_origin_corner": "top-left",
                    "axis_start_index": 0,
                },
                "movement_and_barriers": {
                    "move_set": ["N", "S", "E", "W", "STAY"],
                    "max_barriers": 14,
                    "max_moves": 35,
                    "survival_threshold": 35,
                },
                "scoring": {
                    "capture_cop": 20,
                    "capture_thief": 5,
                    "survival_cop": 5,
                    "survival_thief": 10,
                    "tie_score": 2,
                    "technical_loss": 0,
                },
                "world": {"map_area": "x", "hint_max_words": 15},
                "pheromones": {
                    "pheromone_center_intensity": 0.9,
                    "pheromone_decay": 0.1,
                    "pheromone_grid_size": 5,
                },
                "network_and_league": {
                    "response_timeout_sec": 30,
                    "watchdog_timeout_sec": 30,
                    "num_games": 6,
                    "diversity_reward": 10,
                    "min_games_to_pass": 2,
                    "max_games_per_team": 10,
                    "token_budget_per_series": 200000,
                },
                "rate_limiter_gatekeeper": {
                    "requests_per_minute": 30,
                    "concurrent_requests": 2,
                    "retry_backoff_sec": 5,
                    "max_retries": 3,
                    "queue_depth": 100,
                },
            }
        ),
        encoding="utf-8",
    )
    toml_path = tmp_path / "game.toml"
    toml_path.write_text(
        '[movement_and_barriers]\nmax_moves = 999\n\n[custom]\nlocal_only = "kept"\n',
        encoding="utf-8",
    )

    merged = overlay_toml(json_path, toml_path)

    assert merged["movement_and_barriers"]["max_moves"] == 35  # JSON wins
    assert merged["custom"]["local_only"] == "kept"  # local-only addition survives
