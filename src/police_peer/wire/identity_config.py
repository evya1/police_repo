"""The private TOML's identity, network, model and email sections (book App. B section 4).

`config/game.json` is the signed constitution both peers must match byte for byte. This file
is its opposite: local, private, never signed, never on the wire except for the subset the
greeting carries deliberately. The book's own test decides which is which -- "would the
opponent have to agree to this, or rely on it?" If yes it belongs in the shared JSON; if no it
belongs here.

Every field is optional with a safe default, because a warm-up on a laptop should not need a
filled-in declaration to run. Counted play is where the missing pieces are refused, by name,
and that refusal lives in the composition root rather than here -- a config loader that
raised on an unset team name would make local development impossible for no safety gain.

Two defaults are deliberate rather than convenient: `email.recipient` is the official
v3.0.0 reporting destination, while `email.mode` is `dry-run`. Sending remains opt-in,
twice over (see the reporting root).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from common.config import ConfigError

#: Official counted-report destination from project book v3.0.0.
LECTURER_REPORT_ADDRESS = "rmisegal+uoh26finalgame@gmail.com"


@dataclass(frozen=True, slots=True)
class GameIdentity:
    """Who we are, from `[game]`. Empty values are "not declared", never a placeholder."""

    group_name: str = ""
    group_id: str = ""
    members: tuple[str, ...] = ()
    repos: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Endpoints:
    """From `[network]`: the port we serve and the one thing we know about the opponent."""

    my_port: int = 0
    opponent_url: str = ""
    public_url: str = ""
    turn_timeout_seconds: float | None = None


@dataclass(frozen=True, slots=True)
class LlmSettings:
    """Validated local `[llm]` settings; credentials are deliberately absent."""

    provider: str = "template"
    model: str = "template"
    provider_slug: str | None = None
    step_deadline_seconds: float = 30.0
    max_output_tokens: int = 32
    every_n_steps: int = 1


@dataclass(frozen=True, slots=True)
class EmailSettings:
    """From `[email]`. See the module docstring for why both defaults are what they are."""

    recipient: str = LECTURER_REPORT_ADDRESS
    mode: str = "dry-run"


def _str_map(value: object) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {str(k): str(v) for k, v in value.items()}


def load_game_identity(toml_data: dict) -> GameIdentity:
    """Read `[game]`, tolerating absence."""
    block = toml_data.get("game", {})
    if not isinstance(block, dict):
        return GameIdentity()
    members = block.get("members", [])
    return GameIdentity(
        group_name=str(block.get("group_name", "")),
        group_id=str(block.get("group_id", "")),
        members=tuple(str(m) for m in members) if isinstance(members, list) else (),
        repos=_str_map(block.get("repos")),
    )


def load_endpoints(toml_data: dict) -> Endpoints:
    """Read `[network]`, tolerating absence.

    The turn timeout is read but left as None when unset, so `build_budgets` keeps owning the
    default rather than having two places that both think they decide it.
    """
    block = toml_data.get("network", {})
    if not isinstance(block, dict):
        return Endpoints()
    timeout = block.get("turn_timeout_seconds")
    return Endpoints(
        my_port=int(block.get("my_port", 0) or 0),
        opponent_url=str(block.get("opponent_url", "")),
        public_url=str(block.get("public_url", "")),
        turn_timeout_seconds=float(timeout) if timeout is not None else None,
    )


def load_llm_settings(toml_data: dict) -> LlmSettings:
    """Read `[llm]`; enabled invalid configuration fails during startup."""
    block = toml_data.get("llm", {})
    if not isinstance(block, dict):
        raise ConfigError("[llm] must be a TOML table")
    provider = str(block.get("provider", "template")).strip().lower()
    model = str(block.get("model", "template")).strip()
    raw_provider_slug = block.get("provider_slug")
    provider_slug = str(raw_provider_slug).strip() or None if raw_provider_slug is not None else None
    try:
        deadline = float(block.get("step_deadline_seconds", 30.0))
        max_tokens = int(block.get("max_output_tokens", 32))
        cadence = int(block.get("every_n_steps", 1))
    except (TypeError, ValueError, OverflowError) as exc:
        raise ConfigError("[llm] numeric settings must contain finite numbers") from exc
    if provider not in {"template", "openrouter"}:
        raise ConfigError("[llm].provider must be 'template' or 'openrouter'")
    if provider == "openrouter" and (not model or model == "template"):
        raise ConfigError("[llm].model is required when provider='openrouter'")
    if not 0 < deadline <= 60:
        raise ConfigError("[llm].step_deadline_seconds must be in (0, 60]")
    if not 1 <= max_tokens <= 3200:
        raise ConfigError("[llm].max_output_tokens must be between 1 and 3200")
    if cadence < 1:
        raise ConfigError("[llm].every_n_steps must be at least 1")
    return LlmSettings(provider, model, provider_slug, deadline, max_tokens, cadence)


def load_email_settings(toml_data: dict) -> EmailSettings:
    """Read and validate the local `[email]` delivery mode and recipient."""
    block = toml_data.get("email", {})
    if not isinstance(block, dict):
        raise ConfigError("[email] must be a TOML table")
    recipient = str(block.get("recipient", LECTURER_REPORT_ADDRESS)).strip()
    mode = str(block.get("mode", "dry-run")).strip().lower()
    if mode not in {"off", "dry-run", "send"}:
        raise ConfigError("[email].mode must be 'off', 'dry-run', or 'send'")
    if "\n" in recipient or "\r" in recipient:
        raise ConfigError("[email].recipient must be a single line")
    return EmailSettings(recipient=recipient, mode=mode)
