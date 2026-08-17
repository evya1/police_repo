"""Terms projection and private config wiring.

PRD §9.2 projection table maps the nested ``config/game.json`` contract onto
the flat 14-key signed wire terms. ``min_center_intensity`` is the sole value
that lives in private TOML (FR-11): it has no Appendix-F counterpart and must
be labelled non-official so a mismatch does not trigger a handshake refusal.
"""

from __future__ import annotations

# Exactly 14 keys as specified in the PRD §9.2 projection table.
TERMS_KEYS: frozenset[str] = frozenset({
    "board_size",
    "smell_grid_size",
    "decay_per_step",
    "emit_intensity",
    "min_center_intensity",
    "max_steps",
    "barriers_max",
    "setting",
    "hint_max_words",
    "axis_origin_corner",
    "axis_start_index",
    "thief_start",
    "cop_start",
    "num_games",
})


def project_terms(shared: dict, private: dict) -> dict:
    """Project the 14-key terms table from shared + private inputs.

    Applies the PRD §9.2 projection table. ``num_games`` is fixed at 6.
    ``min_center_intensity`` is sourced from private TOML with a fixed default
    of 0.5 (FR-11, non-official).
    """
    board = shared.get("board_and_agents", {})
    movement = shared.get("movement_and_barriers", {})
    world = shared.get("world", {})
    pheromones = shared.get("pheromones", {})

    return {
        "board_size": board.get("grid_size", 7),
        "smell_grid_size": pheromones.get("pheromone_grid_size", 5),
        "decay_per_step": pheromones.get("pheromone_decay", 0.1),
        "emit_intensity": pheromones.get("pheromone_center_intensity", 0.9),
        "min_center_intensity": private.get("min_center_intensity", 0.5),
        "max_steps": movement.get("max_moves", 35),
        "barriers_max": movement.get("max_barriers", 14),
        "setting": world.get("map_area", "New York"),
        "hint_max_words": world.get("hint_max_words", 15),
        "axis_origin_corner": board.get("axis_origin_corner", "top-left"),
        "axis_start_index": board.get("axis_start_index", 0),
        "thief_start": board.get("thief_start", [3, 3]),
        "cop_start": board.get("cop_start", [0, 0]),
        # num_games is fixed at 6 per PRD §9.2 and known discrepancy O-2.
        "num_games": 6,
    }


def terms_diff(a: dict, b: dict) -> list[str]:
    """Return keys where `a` and `b` disagree (or one is missing)."""
    diffs = []
    all_keys = set(a.keys()) | set(b.keys())
    for key in sorted(all_keys):
        if a.get(key) != b.get(key):
            diffs.append(key)
    return diffs
