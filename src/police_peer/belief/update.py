"""Pure update functions for the belief board.

Fixed half-turn order is pinned in apply_half_turn (PRD §8.1, SD-B2).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from common.domain.board import Cell

if TYPE_CHECKING:
    from .grid import BeliefGrid
    from .probe import EmissionProbe


def diffuse(probs: list[list[float]], size: int) -> list[list[float]]:
    """Spread each cell's mass uniformly over self + 4 orthogonal in-bounds neighbours."""
    new: list[list[float]] = [[0.0] * size for _ in range(size)]
    for r in range(size):
        for c in range(size):
            mass = probs[r][c]
            if mass <= 0.0:
                continue
            neighbourhood = [(r, c)]
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nr, nc = r + dr, c + dc
                if 0 <= nr < size and 0 <= nc < size:
                    neighbourhood.append((nr, nc))
            share = mass / len(neighbourhood)
            for nr, nc in neighbourhood:
                new[nr][nc] += share
    return new


def observe_trust(
    probs: list[list[float]],
    field: dict[str, float],
    trust: float,
    size: int,
) -> list[list[float]]:
    """b(cell) *= (1 + trust * intensity) for received cells; renormalize separately."""
    new = [row[:] for row in probs]
    for key, intensity in field.items():
        try:
            r, c = map(int, key.split(","))
        except ValueError:
            continue
        if 0 <= r < size and 0 <= c < size:
            new[r][c] *= 1.0 + trust * intensity
    return new


def observe_kernel(
    probs: list[list[float]],
    field: dict[str, float],
    trust: float,
    size: int,
    probe: EmissionProbe | None,
) -> list[list[float]]:
    """Full emission-model likelihood against probe.field_at(hypothesis) per cell.

    Shifts factors to be non-negative to avoid negative total mass after multiplication.
    """
    if probe is None:
        raise ValueError("kernel observation requires an EmissionProbe")
    from .probe import kernel_factors

    factors = kernel_factors(size, field, probe, trust)
    min_factor = min(min(row) for row in factors)
    if min_factor < 0:
        shift = 1.0 - min_factor
        factors = [[f + shift for f in row] for row in factors]
    return [
        [probs[r][c] * factors[r][c] for c in range(size)]
        for r in range(size)
    ]


def apply_half_turn(
    grid: BeliefGrid,
    *,
    barrier: Cell | None,
    field: dict[str, float],
    hint: str,
    arena: str,
    own_cell: Cell,
    capture_landed: bool,
) -> None:
    """THE fixed order (PRD §8.1):

    1. exclude(barrier)        [if barrier is not None]
    2. diffuse()
    3. observe_smell(field)
    4. apply_hint(hint, arena)
    5. exclude(own_cell)       [if not capture_landed]

    Barrier is re-excluded after diffusion to prevent mass from leaking back
    onto the impassable cell from neighbouring cells.
    """
    if barrier is not None:
        grid.exclude(barrier)
    grid.diffuse()
    if barrier is not None:
        grid.exclude(barrier)
    grid.observe_smell(field)
    grid.apply_hint(hint, arena)
    if not capture_landed:
        grid.exclude(own_cell)
