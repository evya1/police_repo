"""Shared landmark registry and deterministic hint update (FR-B5, SD-B3).

The ONE landmark table, both directions. Region cells are a project convention
(not official, not signed) — the book fixes the arena name and word cap, not the
board mapping. Both repositories must carry the identical table.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from common.domain.board import Cell

if TYPE_CHECKING:
    from .grid import BeliefGrid

# The ONE landmark table, both directions.
LANDMARK_CELLS: dict[str, dict[str, list[Cell]]] = {
    "New York": {
        "The Bronx":      [(0, 0), (0, 1), (1, 0)],
        "Central Park":   [(1, 2), (1, 3), (1, 4)],
        "Manhattan":      [(2, 2), (3, 2), (4, 2)],
        "Times Square":   [(3, 3), (3, 4), (4, 3)],
        "Brooklyn":       [(5, 4), (6, 4), (6, 5)],
    },
}

GENERIC_FALLBACK: dict[str, tuple[Cell, ...]] = {
    "north":  ((0, 2), (0, 3), (0, 4)),
    "south":  ((6, 2), (6, 3), (6, 4)),
    "east":   ((2, 6), (3, 6), (4, 6)),
    "west":   ((2, 0), (3, 0), (4, 0)),
    "center": ((3, 3),),
}


def parse_landmarks(hint: str, arena: str, board_size: int) -> list[Cell]:
    """Case-insensitive substring match of registered landmark names.

    Pure deterministic parser returning matched region cells.
    """
    hint_lower = hint.lower()
    matched: list[Cell] = []

    if arena in LANDMARK_CELLS:
        for landmark_name, cells in LANDMARK_CELLS[arena].items():
            if landmark_name.lower() in hint_lower:
                matched.extend(cells)

    if not matched:
        for word, cells in GENERIC_FALLBACK.items():
            if word in hint_lower:
                matched.extend(cells)

    # Deduplicate while preserving order
    seen: set[tuple[int, int]] = set()
    result: list[Cell] = []
    for cell in matched:
        if cell not in seen:
            seen.add(cell)
            result.append(cell)
    return result


def apply_hint(
    grid: BeliefGrid,
    hint: str,
    arena: str,
    board_size: int,
    hint_reliability: float,
) -> None:
    """For each matched cell: b *= (1 + rel * w(d)), w(0)=1; renormalize."""
    cells = parse_landmarks(hint, arena, board_size)
    if not cells:
        return

    # All matched cells are IN the region, so distance from region = 0, w(0) = 1.
    weight = 1.0
    for cell in cells:
        r, c = cell
        if 0 <= r < board_size and 0 <= c < board_size:
            matrix = grid._matrix
            matrix[r][c] *= 1.0 + hint_reliability * weight
    grid._normalize()
