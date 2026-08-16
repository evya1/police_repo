"""Subtractive Chebyshev scent profile (reference-v3 / kit first interoperability profile).

Ported verbatim from ``verify_vectors.py`` (upstream commit ad6557626587e09146af4283a5e808e7001343c5,
EVID-003 revision) — the arithmetic must not be re-derived.

M-01 §B.1: linear Chebyshev falloff, subtractive decay, rounded to 3 places,
deposit-then-decay, max-merge, lower clamp only, transmitted.
"""

from __future__ import annotations


def smell_emit(center: tuple[int, int], intensity: float, grid_size: int,
               board_size: int) -> dict[str, float]:
    """Radial scent emission around a cell (book ch.4; reference domain/smell.py).

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
