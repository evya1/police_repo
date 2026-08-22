"""Tests for wire/config.py — build_peer_config + assemble_peer_config assembly.

CFG-003: JSON overlays TOML on conflict; private values override defaults.
num_games is pinned to 6 by the assembler regardless of the JSON value (O-2).
The shared terms document comes from the ``valid_terms_data`` fixture.
"""

from __future__ import annotations

import json
from pathlib import Path

from police_peer.wire.config import (
    PrivateConfig,
    assemble_peer_config,
    build_peer_config,
    verify_terms_closed,
)


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


class TestBuildPeerConfig:
    """Tests for build_peer_config — JSON + TOML assembly, CFG-003."""

    def test_returns_closed_terms(self, tmp_path: Path, valid_terms_data: dict) -> None:
        json_path = tmp_path / "game.json"
        _write_json(json_path, valid_terms_data)
        terms = build_peer_config(json_path, PrivateConfig())
        errors = verify_terms_closed(terms)
        assert errors == []

    def test_num_games_fixed_at_six(self, tmp_path: Path, valid_terms_data: dict) -> None:
        # JSON says num_games=1 (known discrepancy O-2); the assembler pins it to 6.
        valid_terms_data["network_and_league"]["num_games"] = 1
        json_path = tmp_path / "game.json"
        _write_json(json_path, valid_terms_data)
        terms = build_peer_config(json_path, PrivateConfig())
        assert terms["num_games"] == 6

    def test_setting_from_json(self, tmp_path: Path, valid_terms_data: dict) -> None:
        valid_terms_data["world"]["map_area"] = "Haifa"
        json_path = tmp_path / "game.json"
        _write_json(json_path, valid_terms_data)
        terms = build_peer_config(json_path, PrivateConfig())
        assert terms["setting"] == "Haifa"

    def test_private_min_center_intensity_overrides_default(
        self, tmp_path: Path, valid_terms_data: dict
    ) -> None:
        json_path = tmp_path / "game.json"
        _write_json(json_path, valid_terms_data)
        private = PrivateConfig(min_center_intensity=0.8)
        terms = build_peer_config(json_path, private)
        assert terms["min_center_intensity"] == 0.8

    def test_private_min_center_intensity_default(self, tmp_path: Path, valid_terms_data: dict) -> None:
        json_path = tmp_path / "game.json"
        _write_json(json_path, valid_terms_data)
        private = PrivateConfig()
        terms = build_peer_config(json_path, private)
        assert terms["min_center_intensity"] == 0.5


class TestAssemblePeerConfig:
    """Tests for assemble_peer_config — full PeerConfig assembly."""

    def test_returns_expected_keys(self, tmp_path: Path, valid_terms_data: dict) -> None:
        json_path = tmp_path / "game.json"
        _write_json(json_path, valid_terms_data)
        result = assemble_peer_config(json_path, PrivateConfig(), "police")
        assert "terms" in result
        assert "natural_role" in result
        assert "seed" in result
        assert "budgets" in result
        assert result["natural_role"] == "police"

    def test_terms_are_closed(self, tmp_path: Path, valid_terms_data: dict) -> None:
        json_path = tmp_path / "game.json"
        _write_json(json_path, valid_terms_data)
        result = assemble_peer_config(json_path, PrivateConfig(), "police")
        errors = verify_terms_closed(result["terms"])
        assert errors == []

    def test_num_games_overridden(self, tmp_path: Path, valid_terms_data: dict) -> None:
        valid_terms_data["network_and_league"]["num_games"] = 1
        json_path = tmp_path / "game.json"
        _write_json(json_path, valid_terms_data)
        result = assemble_peer_config(json_path, PrivateConfig(), "thief")
        assert result["terms"]["num_games"] == 6
