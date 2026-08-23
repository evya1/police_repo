"""Injection seam: config-selected brain, fail-fast.

Shared core (mirrors thief_repo identically modulo import path and role constant).
"""

from __future__ import annotations

import random
from collections.abc import Mapping
from importlib import import_module

from common.domain.scoring import Role

from .base import BrainBase
from .hint_types import TextProvider

_SELECTORS: dict[Role, str] = {
    Role.THIEF: "thief_class",
    Role.POLICE: "police_class",
}


def resolve_brain_cls(
    config: Mapping[str, object] | None, role: Role
) -> type[BrainBase]:
    """The config selector ([strategy] thief_class / police_class, dotted
    "package.module:ClassName") if set, else the shipped default for `role`
    (police_repo: PoliceBrain; the opposite-role default is PLAN SD-P7).

    Fail-fast: ValueError on malformed selector / missing attribute; TypeError
    if the target is not a BrainBase subclass.
    """
    if config is None:
        return _default_cls(role)
    selector_key = _SELECTORS[role]
    strategy = config.get("strategy")
    if not isinstance(strategy, Mapping):
        return _default_cls(role)
    selector = strategy.get(selector_key)
    if selector is None:
        return _default_cls(role)
    if not isinstance(selector, str) or ":" not in selector:
        raise ValueError(f"malformed brain selector {selector!r} for {role}")
    module_path, class_name = selector.rsplit(":", 1)
    try:
        mod = import_module(module_path)
    except ModuleNotFoundError as exc:
        raise ValueError(f"brain module {module_path!r} not found for {role}") from exc
    cls = getattr(mod, class_name, None)
    if cls is None:
        raise ValueError(f"brain class {class_name!r} not found in {module_path}")
    if not (isinstance(cls, type) and issubclass(cls, BrainBase)):
        raise TypeError(f"{class_name} is not a BrainBase subclass")
    return cls


def resolve_brain(
    config: Mapping[str, object] | None,
    role: Role,
    llm: TextProvider | None = None,
    rng: random.Random | None = None,
) -> BrainBase:
    """Instantiate the resolved class with: rng (default: seeded from the
    resolved config's seed), arena + hint_max_words from the resolved config,
    and a HintWriter carrying `llm` as its optional TextProvider (T027; closes
    F-14 -- `llm` is used, or rejected fail-fast, never silently ignored). The
    C04 runtime never hard-codes a brain (book section 6.2, runtime.py L73).
    """
    cls = resolve_brain_cls(config, role)
    if rng is None:
        seed = 0
        if config is not None:
            seed = int(config.get("seed", 0))
        rng = random.Random(seed)

    arena = "New York"
    max_words = 15
    if config is not None:
        world = config.get("world")
        if isinstance(world, Mapping):
            arena = str(world.get("map_area", "New York"))
            max_words = int(world.get("hint_max_words", 15))

    from .hints import HintWriter

    if llm is not None and not isinstance(llm, TextProvider):
        raise TypeError(f"llm={llm!r} does not implement TextProvider.render")
    hint_writer = HintWriter(role, rng, arena, max_words, provider=llm)
    kwargs: dict[str, object] = {"rng": rng, "arena": arena, "max_words": max_words,
                                  "hint_writer": hint_writer}
    # Apply role-specific config weights (PRD §9).
    if config is not None:
        role_cfg = config.get("strategy", {}).get(role.value if isinstance(role, Role) else str(role), {})
        if isinstance(role_cfg, Mapping):
            kwargs.update({
                "min_confidence": float(role_cfg.get("min_confidence", 0.10)),
                "barrier_mass_floor": float(role_cfg.get("barrier_mass_floor", 0.05)),
                "w_mass": float(role_cfg.get("w_mass", 1.0)),
                "w_cut": float(role_cfg.get("w_cut", 0.5)),
                "route_slack": int(role_cfg.get("route_slack", 1)),
                "barrier_reserve": int(role_cfg.get("barrier_reserve", 3)),
                "strong_threshold": float(role_cfg.get("strong_threshold", 0.8)),
                "barrier_score_threshold": float(role_cfg.get("barrier_score_threshold", 0.3)),
            })
    return cls(**kwargs)


def _default_cls(role: Role) -> type[BrainBase]:
    """Return the shipped default brain class for the role."""
    if role is Role.POLICE:
        from .police import PoliceBrain
        return PoliceBrain
    # THIEF default: stand-in kept on this repo (SD-P7).
    raise ValueError(f"no default brain class for {role} in police_repo")
