"""Wire-boundary evidence normalization — the ONE place untrusted public

turn fields are validated before they reach the belief board or the brain.

The opponent's ``TurnMessage`` is untrusted input (it may be buggy or
hostile): a malformed ``smell_grid`` must never crash the honest peer's own
turn (H3 -- previously an unguarded ``int()`` on the wire keys turned a bad
message into a mid-turn exception and a technical loss for the *honest*
side). This module is the single normalization boundary; nothing else in
``strategy/``, ``belief/`` or ``scent/`` re-parses raw wire evidence.
"""

from __future__ import annotations

from collections.abc import Mapping

from common.domain.board import Board, Cell


def normalize_scent_field(raw: object, board: Board) -> dict[str, float]:
    """Return a clean ``{"r,c": intensity}`` snapshot from an untrusted public field.

    - Non-mapping input -> ``{}`` (never raises).
    - Only keys of the exact wire shape ``"r,c"`` (two integers) survive.
    - Coordinates outside the board are discarded.
    - Booleans, non-numeric, NaN, and infinite intensities are discarded.
    - The scent contract (``docs/contracts``) does not declare an upper bound
      on emitted intensity, so none is invented here: a surviving value only
      has to be finite and nonnegative.
    - The returned dict is always a fresh object -- the caller's mutable dict
      (if any) is never retained.
    """
    clean: dict[str, float] = {}
    if not isinstance(raw, Mapping):
        return clean
    for key, value in raw.items():
        cell = _parse_cell(key)
        if cell is None or not board.in_bounds(cell):
            continue
        intensity = _parse_intensity(value)
        if intensity is None:
            continue
        clean[f"{cell[0]},{cell[1]}"] = intensity
    return clean


def _parse_cell(key: object) -> Cell | None:
    if not isinstance(key, str):
        return None
    parts = key.split(",")
    if len(parts) != 2:
        return None
    try:
        return (int(parts[0]), int(parts[1]))
    except ValueError:
        return None


def _parse_intensity(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    score = float(value)
    if score != score or score in (float("inf"), float("-inf")):  # NaN / inf
        return None
    if score < 0.0:
        return None
    return score
