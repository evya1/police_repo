"""Private LLM configuration and production composition tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from common.config import ConfigError
from police_peer.wire.config import load_private
from police_peer.wire.identity_config import LlmSettings
from police_peer.wire.llm_composition import compose_text_provider


def _write(path: Path, llm: str) -> Path:
    path.write_text(f"[llm]\n{llm}\n", encoding="utf-8")
    return path


def test_absent_llm_config_defaults_to_offline_template(tmp_path: Path) -> None:
    settings = load_private(tmp_path / "absent.toml").llm
    assert settings.provider == "template"
    assert compose_text_provider(settings, {}) is None


def test_template_mode_constructs_neither_client_nor_gatekeeper(monkeypatch) -> None:
    def forbidden(*_args, **_kwargs):
        raise AssertionError("template mode allocated a network dependency")

    monkeypatch.setattr("police_peer.wire.llm_composition.OpenRouterClient", forbidden)
    monkeypatch.setattr("police_peer.wire.llm_composition.ExternalApiGatekeeper", forbidden)
    assert compose_text_provider(LlmSettings(), {}, environment={}) is None


def test_openrouter_without_key_fails_at_composition() -> None:
    settings = LlmSettings(
        provider="openrouter", model="inclusionai/ling-3.0-flash", provider_slug="novita",
    )
    with pytest.raises(ConfigError, match="OPENROUTER_API_KEY"):
        compose_text_provider(settings, {}, environment={})


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ('provider = "openrouter"\nmodel = ""\nprovider_slug = "novita"', "model"),
        ('provider = "openrouter"\nmodel = "m"\nprovider_slug = ""', "provider_slug"),
        ('provider = "ollama"', "provider"),
        ('provider = "openrouter"\nmodel = "m"\nprovider_slug = "p"\nmax_output_tokens = 65',
         "max_output_tokens"),
        ('provider = "openrouter"\nmodel = "m"\nprovider_slug = "p"\nevery_n_steps = 0',
         "every_n_steps"),
    ],
)
def test_invalid_enabled_configuration_fails_during_load(
    tmp_path: Path, text: str, message: str,
) -> None:
    with pytest.raises(ConfigError, match=message):
        load_private(_write(tmp_path / "game.toml", text))


def test_openrouter_settings_parse_all_production_fields(tmp_path: Path) -> None:
    settings = load_private(_write(
        tmp_path / "game.toml",
        '\n'.join((
            'provider = "openrouter"', 'model = "inclusionai/ling-3.0-flash"',
            'provider_slug = "novita"', 'step_deadline_seconds = 12',
            'max_output_tokens = 8', 'every_n_steps = 2',
        )),
    )).llm
    assert settings == LlmSettings(
        "openrouter", "inclusionai/ling-3.0-flash", "novita", 12.0, 8, 2,
    )
