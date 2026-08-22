"""Tests for wire/config.py — PrivateConfig, load_private, verify_terms_closed.

CFG-003: JSON overlays TOML on conflict; TOML may add local-only keys. The
build/assemble coverage lives in test_config_assembly.py.
"""

from __future__ import annotations

from pathlib import Path

from police_peer.wire.config import (
    PrivateConfig,
    load_private,
    verify_terms_closed,
)


class TestPrivateConfig:
    """Tests for PrivateConfig dataclass."""

    def test_defaults(self) -> None:
        cfg = PrivateConfig()
        assert cfg.min_center_intensity == 0.5
        assert cfg.group_id == ""
        assert cfg.seed == 0
        assert cfg.budgets == {}

    def test_custom_values(self) -> None:
        cfg = PrivateConfig(min_center_intensity=0.7, group_id="team-x", seed=42)
        assert cfg.min_center_intensity == 0.7
        assert cfg.group_id == "team-x"
        assert cfg.seed == 42


class TestLoadPrivate:
    """Tests for load_private — reads game.toml."""

    def test_missing_file_returns_defaults(self, tmp_path: Path) -> None:
        result = load_private(tmp_path / "missing.toml")
        assert isinstance(result, PrivateConfig)
        assert result.min_center_intensity == 0.5

    def test_reads_min_center_intensity(self, tmp_path: Path) -> None:
        toml = tmp_path / "game.toml"
        toml.write_text('min_center_intensity = 0.7\n', encoding="utf-8")
        result = load_private(toml)
        assert result.min_center_intensity == 0.7

    def test_reads_group_id(self, tmp_path: Path) -> None:
        toml = tmp_path / "game.toml"
        toml.write_text('group_id = "my-team"\n', encoding="utf-8")
        result = load_private(toml)
        assert result.group_id == "my-team"

    def test_reads_seed(self, tmp_path: Path) -> None:
        toml = tmp_path / "game.toml"
        toml.write_text('seed = 1234\n', encoding="utf-8")
        result = load_private(toml)
        assert result.seed == 1234


class TestVerifyTermsClosed:
    """Tests for verify_terms_closed — detects deviations from TERMS_KEYS."""

    def test_no_errors_when_closed(self) -> None:
        from common.transport.terms import TERMS_KEYS
        terms = dict.fromkeys(TERMS_KEYS, 0)
        assert verify_terms_closed(terms) == []

    def test_missing_key_detected(self) -> None:
        from common.transport.terms import TERMS_KEYS
        terms = dict.fromkeys(TERMS_KEYS, 0)
        del terms["num_games"]
        errors = verify_terms_closed(terms)
        assert "num_games" in errors

    def test_extra_key_detected(self) -> None:
        from common.transport.terms import TERMS_KEYS
        terms = dict.fromkeys(TERMS_KEYS, 0)
        terms["extra_key"] = 1
        errors = verify_terms_closed(terms)
        assert "extra_key" in errors

    def test_multiple_errors(self) -> None:
        from common.transport.terms import TERMS_KEYS
        terms = dict.fromkeys(TERMS_KEYS, 0)
        del terms["num_games"]
        terms["extra"] = 1
        errors = verify_terms_closed(terms)
        assert "extra" in errors
        assert "num_games" in errors
