"""Emission probe seam for the locked scent profile (FR-B9, ADR-004).

The belief module obtains the locked scent model's emission kernel
exclusively through this narrow seam — never importing a profile directly.
"""

from __future__ import annotations

from typing import Protocol

from common.domain.board import Cell


class EmissionProbe(Protocol):
    """Narrow seam to the locked scent profile (FR-B9, ADR-004)."""

    def field_at(self, center: Cell) -> dict[str, float]:
        """Pure radial emission at hypothetical centre."""
        ...


def kernel_factors(
    size: int,
    field: dict[str, float],
    probe: EmissionProbe,
    trust: float,
) -> list[list[float]]:
    """Per-hypothesis-cell likelihood factor for the received field.

    fit(s) = average similarity between observed field and probe.field_at(s),
    normalized to [0, 1]; factor(s) = 1 + trust * (fit(s) - 0.5).
    Empty field => uniform negative evidence (1 - trust) for all cells.
    Similarity uses max_diff=0.9 (max emission intensity) for normalization.
    """
    result: list[list[float]] = [[1.0] * size for _ in range(size)]
    max_diff = 0.9

    if not field:
        for r in range(size):
            for c in range(size):
                result[r][c] = 1.0 - trust
        return result

    for r in range(size):
        for c in range(size):
            hyp_field = probe.field_at((r, c))
            score = 0.0
            for field_key, obs_val in field.items():
                kernel_val = hyp_field.get(field_key, 0.0)
                diff = abs(obs_val - kernel_val)
                similarity = max(0.0, 1.0 - diff / max_diff)
                score += similarity
            fit = score / len(field)
            result[r][c] = 1.0 + trust * (fit - 0.5)

    return result
