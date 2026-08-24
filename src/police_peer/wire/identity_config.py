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

Two defaults are deliberate rather than convenient:

* `email.recipient` defaults to the lecturer's reporting address (App. F table 20), because
  that is the only address a report may ever go to, and a typo'd override should look wrong
  rather than silently mail nobody.
* `email.mode` defaults to `dry-run`. Sending is opt-in, twice over (see the reporting root).
"""

from __future__ import annotations

from dataclasses import dataclass, field

#: App. F table 20 -- the one address the agent's automated reports may target.
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
    """From `[llm]`. `model` is declared in the pre-game identity, so it is not cosmetic."""

    model: str = "template"
    step_deadline_seconds: float = 30.0


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
    """Read `[llm]`, tolerating absence."""
    block = toml_data.get("llm", {})
    if not isinstance(block, dict):
        return LlmSettings()
    return LlmSettings(
        model=str(block.get("model", "template")),
        step_deadline_seconds=float(block.get("step_deadline_seconds", 30.0)),
    )


def load_email_settings(toml_data: dict) -> EmailSettings:
    """Read `[email]`, tolerating absence."""
    block = toml_data.get("email", {})
    if not isinstance(block, dict):
        return EmailSettings()
    return EmailSettings(
        recipient=str(block.get("recipient", LECTURER_REPORT_ADDRESS)),
        mode=str(block.get("mode", "dry-run")),
    )
