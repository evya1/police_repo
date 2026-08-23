"""Physics checks armed from the 14 signed terms.

Position trail validation, orthogonal step enforcement, barrier quota, and step ceiling.
All checks derive from the position trail — never the peer's move spelling (FR-26/FR-27).

The trail is read from the record's explicit sealed ``position`` where present, falling
back to parsing the ``state`` string. That order matters for interoperability: `state` is
spelled to *our* convention, and a conforming peer that spells it differently used to make
every physics check silently skip — no answer, presented as a clean one. An explicit
position is parsed strictly (two real ints, never a bool); anything else degrades to the
`state` fallback rather than being loosely re-read into the wrong cell, and an unreadable
record skips the physics layer rather than manufacturing an accusation.
"""

from __future__ import annotations

import re


def check_physics(records: list[dict], terms: dict) -> list[tuple[int, str]]:
    """Check physics across all records. Returns list of (step, problem) tuples."""
    problems: list[tuple[int, str]] = []
    prev_pos: tuple[int, int] | None = None
    board_size = terms.get("board_size", 7)
    max_steps = terms.get("max_steps", 35)
    barriers_max = terms.get("barriers_max", 14)

    for record in records:
        step = int(record.get("step", 0))
        if step < 1:
            continue

        state = record.get("state", "")
        pos = parse_kit_position(record) or _parse_position(state)

        if pos is not None:
            r, c = pos
            if not (0 <= r < board_size and 0 <= c < board_size):
                problems.append((step, f"position ({r},{c}) off {board_size}x{board_size} board"))
            if prev_pos is not None:
                dr = abs(r - prev_pos[0])
                dc = abs(c - prev_pos[1])
                if dr + dc > 1:
                    problems.append((step, f"jump {prev_pos} -> ({r},{c}) > 1 orthogonal step"))
            prev_pos = (r, c)

        if step > max_steps + 1:
            problems.append((step, f"step {step} exceeds ceiling {max_steps + 1}"))

        barrier_count = _count_barriers(state)
        if barrier_count > barriers_max:
            problems.append((step, f"barrier count {barrier_count} exceeds quota {barriers_max}"))

    return problems


def parse_kit_position(payload: dict) -> tuple[int, int] | None:
    """Strictly parse a kit-style `position: [r, c]`, or None.

    Strict on purpose: exactly two real ints (a bool is not an int here, however much
    Python disagrees). Anything else returns None so the caller degrades to the `state`
    fallback -- never a loose parse that could mis-read a malformed payload into the wrong
    cell and then accuse the peer of moving there.
    """
    pos = payload.get("position") if isinstance(payload, dict) else None
    if (
        isinstance(pos, (list, tuple))
        and len(pos) == 2
        and all(isinstance(v, int) and not isinstance(v, bool) for v in pos)
    ):
        return (int(pos[0]), int(pos[1]))
    return None


def _parse_position(state: str) -> tuple[int, int] | None:
    """Extract position from the sealed state string."""
    match = re.search(r"self=\[(-?\d+),\s*(-?\d+)\]", state)
    if match:
        return int(match.group(1)), int(match.group(2))
    return None


def _count_barriers(state: str) -> int:
    """Count barriers in the sealed state string."""
    match = re.search(r"barriers=\[(.+)\]", state)
    if match:
        inner = match.group(1).strip()
        if inner and inner != "[]":
            return inner.count("[")
    return 0
