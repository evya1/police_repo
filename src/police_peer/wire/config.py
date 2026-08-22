"""Private config (TOML) + PeerConfig assembly from the shared JSON contract.

Loads the local-only ``game.toml`` into a ``PrivateConfig`` and assembles a
``PeerConfig`` (from ``common.transport.series``) by projecting the C01-
validated ``game.json`` snapshot through ``project_terms``.  JSON wins on any
conflict (CFG-003): TOML may add local-only settings but never weakens a
signed condition.
"""

from __future__ import annotations

import tomllib  # Python 3.11+
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from common.config import ConfigError, load_config
from common.transport.terms import TERMS_KEYS, project_terms
from police_peer.scent.lock import model_lock_hash
from police_peer.scent.model import DEFAULT_MODEL, MODELS


@dataclass
class PrivateConfig:
    """Local-only configuration loaded from ``game.toml``.

    ``min_center_intensity`` is the only wire-relevant value permitted here
    (FR-11, non-official).  All other fields are purely local — peer identity,
    budgets, transport settings — and never cross the network.
    """

    min_center_intensity: float = 0.5
    group_id: str = ""
    seed: int = 0
    budgets: dict[str, float] = field(default_factory=dict)
    scent_model: str = DEFAULT_MODEL


def load_private(path: Path | str) -> PrivateConfig:
    """Load ``game.toml`` and return a ``PrivateConfig`` instance."""
    path = Path(path)
    if not path.is_file():
        return PrivateConfig()
    with open(path, "rb") as f:
        toml_data = tomllib.load(f)
    scent_model = str(toml_data.get("scent_model", DEFAULT_MODEL))
    if scent_model not in MODELS:
        raise ConfigError(
            f"unknown scent_model {scent_model!r}; expected one of {list(MODELS)}"
        )
    return PrivateConfig(
        min_center_intensity=float(toml_data.get("min_center_intensity", 0.5)),
        group_id=str(toml_data.get("group_id", "")),
        seed=int(toml_data.get("seed", 0)),
        budgets={k: float(v) for k, v in toml_data.get("network", {}).items()},
        scent_model=scent_model,
    )


class Budgets:
    """Turn budgets satisfying ``common.transport.series.Budgets``.

    The series engine reads these as attributes, so a plain dict cannot stand in
    for them -- assembling one the documented way used to hand ``PeerConfig`` a
    dict and fail with ``AttributeError`` at the first wait.
    """

    def __init__(
        self,
        turn_timeout: float = 30.0,
        connect_timeout: float = 30.0,
        poll_interval: float = 0.01,
    ) -> None:
        self.turn_timeout = turn_timeout
        self.connect_timeout = connect_timeout
        self.poll_interval = poll_interval


def build_budgets(
    private: PrivateConfig,
    overrides: dict[str, float] | None = None,
) -> Budgets:
    """Single construction point for turn budgets: private TOML, then overrides."""
    merged: dict[str, float] = {**private.budgets, **(overrides or {})}
    return Budgets(
        turn_timeout=float(merged.get("turn_timeout", 30.0)),
        connect_timeout=float(merged.get("connect_timeout", 30.0)),
        poll_interval=float(merged.get("poll_interval", 0.01)),
    )


def peer_locks(private: PrivateConfig) -> dict[str, str]:
    """Hashes of the physics this peer has pinned, keyed by lock family.

    The scent model is a local choice, so the only way an opponent can tell that
    we run different physics is if we declare the hash in the greeting. Without
    this, ``verify_greeting`` sees no declaration, treats silence as agreement,
    and a counted game starts with the two peers emitting different scent fields.
    """
    return {"scent_model": model_lock_hash(private.scent_model)}


def build_peer_config(
    json_path: Path | str,
    private: PrivateConfig,
) -> dict[str, Any]:
    """Assemble a ``PeerConfig`` terms dict from validated JSON + private TOML.

    ``CFG-003``: the shared JSON value wins on every conflict; TOML may only
    contribute keys absent from the JSON contract (e.g. ``min_center_intensity``).
    ``num_games`` is enforced to be 6 regardless of what the JSON declares.
    """
    shared = load_config(json_path)
    terms = project_terms(shared, private.__dict__)
    # num_games is fixed at 6 — override whatever the JSON says (O-2).
    terms["num_games"] = 6
    return terms


def assemble_peer_config(
    json_path: Path | str,
    private: PrivateConfig,
    natural_role: str,
    budgets: dict[str, float] | None = None,
    seed: int = 0,
) -> dict[str, Any]:
    """Full ``PeerConfig`` assembly: terms + metadata.

    Returns a dict with keys ``terms``, ``natural_role``, ``seed``, ``budgets``
    and ``locks`` so callers can construct a
    ``common.transport.series.PeerConfig`` directly.
    """
    terms = build_peer_config(json_path, private)
    return {
        "terms": terms,
        "natural_role": natural_role,
        "seed": seed or private.seed,
        "budgets": build_budgets(private, budgets),
        "locks": peer_locks(private),
    }


def verify_terms_closed(terms: dict[str, Any]) -> list[str]:
    """Return missing or extra keys when ``terms`` deviates from ``TERMS_KEYS``."""
    missing = sorted(set(TERMS_KEYS) - set(terms))
    extra = sorted(set(terms) - set(TERMS_KEYS))
    return missing + extra
