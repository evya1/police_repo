"""Normalized private ``[strategy]`` settings — one typed record, not a dict.

Split out of ``wire/config.py`` (line cap) but part of the same startup
normalization boundary: raw TOML shape is parsed exactly once, here, into
``StrategySettings``; nothing downstream (the brain, the inject seam, the
wire adapters) re-parses ``[strategy]`` / ``[strategy.police]`` for itself.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from police_peer.wire.config import PrivateConfig


@dataclass(frozen=True, slots=True)
class StrategySettings:
    """Normalized ``[strategy]`` / ``[strategy.<role>]`` private config (PRD §9)."""

    police_class: str | None = None
    police_weights: dict[str, float] = field(default_factory=dict)


def load_strategy_settings(toml_data: dict) -> StrategySettings:
    """Parse the raw ``[strategy]`` TOML table into a ``StrategySettings`` record."""
    strategy = toml_data.get("strategy", {})
    if not isinstance(strategy, dict):
        return StrategySettings()
    police_class = strategy.get("police_class")
    police_section = strategy.get("police", {})
    weights = (
        {k: float(v) for k, v in police_section.items()}
        if isinstance(police_section, dict)
        else {}
    )
    return StrategySettings(
        police_class=str(police_class) if police_class is not None else None,
        police_weights=weights,
    )


def assemble_strategy_config(
    private: PrivateConfig, shared: dict[str, Any], seed: int = 0,
) -> dict[str, Any]:
    """Build the ``resolve_brain``-shaped mapping from validated shared JSON + private TOML.

    ONE place assembles this shape (``{"seed", "world", "strategy": {...},
    "scent_model": ...}``) instead of every call site hand-building a nested
    dict; ``resolve_brain`` and the wire adapters both consume this, and no
    strategy module reads a config file or global state itself.
    """
    world = shared.get("world", {}) if isinstance(shared, dict) else {}
    strategy_cfg: dict[str, Any] = {"police": dict(private.strategy.police_weights)}
    if private.strategy.police_class:
        strategy_cfg["police_class"] = private.strategy.police_class
    return {
        "seed": seed or private.seed,
        "world": {
            "map_area": world.get("map_area", "New York"),
            "hint_max_words": world.get("hint_max_words", 15),
        },
        "strategy": strategy_cfg,
        "scent_model": private.scent_model,
        "llm": {
            "step_deadline_seconds": private.llm.step_deadline_seconds,
            "every_n_steps": private.llm.every_n_steps,
        },
    }
