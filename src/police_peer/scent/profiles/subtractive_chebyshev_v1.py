"""Subtractive Chebyshev scent profile — the reference-v3 default.

Implements M-01 §B.1, from the official game book (Book v3.0.0, ch. 4): linear Chebyshev
falloff, subtractive decay, rounded to 3 places, deposit-then-decay, max-merge, lower clamp
only, transmitted. The behavior is pinned by ``vectors/pheromone.json``.
"""

from __future__ import annotations


def smell_emit(center: tuple[int, int], intensity: float, grid_size: int,
               board_size: int) -> dict[str, float]:
    """Radial scent emission around a cell (book ch.4, M-01 §B.1).

    half = grid_size // 2 ; falloff = intensity / (half + 1)
    value(cell) = round(max(0.0, intensity - falloff * chebyshev(cell, center)), 3)

    Returns the wire/snapshot form {"r,c": value} for cells inside the board with value > 0.
    """
    half = grid_size // 2
    falloff = intensity / (half + 1)
    out: dict[str, float] = {}
    for dr in range(-half, half + 1):
        for dc in range(-half, half + 1):
            r, c = center[0] + dr, center[1] + dc
            if 0 <= r < board_size and 0 <= c < board_size:
                value = round(max(0.0, intensity - falloff * max(abs(dr), abs(dc))), 3)
                if value > 0.0:
                    out[f"{r},{c}"] = value
    return out


def smell_decay(values: dict[str, float], decay: float) -> dict[str, float]:
    """One game-step decay: every intensity drops by the constant, clamped at 0 (rounded to 3)."""
    return {k: round(max(0.0, v - decay), 3) for k, v in values.items()}
