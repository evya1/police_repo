"""BeliefGrid — a normalized P(opponent = cell) over an NxN board.

Local inference only. No RNG, no I/O, no hidden-truth leakage (FR-B7, FR-B8).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from common.domain.board import Board, Cell

if TYPE_CHECKING:
    from .probe import EmissionProbe

_EPSILON = 1e-9


class BeliefGrid:
    """Normalized P(opponent = cell) over an NxN board. Local inference only."""

    def __init__(
        self,
        board: Board,
        *,
        trust: float = 4.0,
        update_form: str = "trust_v1",
        hint_reliability: float = 0.25,
        probe: EmissionProbe | None = None,
    ) -> None:
        if update_form not in ("trust_v1", "kernel_bayes_v1"):
            raise ValueError(f"unknown update_form {update_form!r}")
        if update_form == "kernel_bayes_v1" and probe is None:
            raise ValueError("kernel_bayes_v1 requires an EmissionProbe")
        self._board = board
        self._trust = trust
        self._update_form = update_form
        self._hint_reliability = hint_reliability
        self._probe = probe
        size = board.size
        self._allowed: set[Cell] = {
            (r, c) for r in range(size) for c in range(size)
        }
        self._matrix: list[list[float]] = [
            [1.0 / (size * size)] * size for _ in range(size)
        ]

    # -- queries (FR-B6) -------------------------------------------------

    def prob(self, cell: Cell) -> float:
        r, c = cell
        if not self._board.in_bounds(cell):
            return 0.0
        return self._matrix[r][c]

    def most_likely(self) -> Cell:
        """argmax with lexicographic tie-break (row, col)."""
        best: Cell = (0, 0)
        best_prob = -1.0
        for r in range(self._board.size):
            for c in range(self._board.size):
                p = self._matrix[r][c]
                if p > best_prob:
                    best_prob = p
                    best = (r, c)
        return best

    def peak_probability(self) -> float:
        return max(max(row) for row in self._matrix)

    def top_k(self, k: int) -> list[tuple[Cell, float]]:
        cells = [
            (r, c)
            for r in range(self._board.size)
            for c in range(self._board.size)
        ]
        cells.sort(key=lambda cell: (-self._matrix[cell[0]][cell[1]], cell[0], cell[1]))
        return [(cell, self._matrix[cell[0]][cell[1]]) for cell in cells[:k]]

    def as_matrix(self) -> list[list[float]]:
        """Deep copy (OBS-003)."""
        return [row[:] for row in self._matrix]

    @property
    def allowed_cells(self) -> set[Cell]:
        return set(self._allowed)

    # -- updates (called by update.py; kept public for testability) -------

    def exclude(self, cell: Cell) -> None:
        """Zero cell, remove from allowed set, and renormalize (FR-B4)."""
        if self._board.in_bounds(cell):
            self._allowed.discard(cell)
            self._matrix[cell[0]][cell[1]] = 0.0
        self._normalize()

    def diffuse(self) -> None:
        """Spread each cell's mass uniformly over self + in-bounds ortho neighbours (FR-B3)."""
        size = self._board.size
        new_matrix: list[list[float]] = [[0.0] * size for _ in range(size)]
        new_allowed: set[Cell] = set()
        for r in range(size):
            for c in range(size):
                mass = self._matrix[r][c]
                if mass <= 0.0:
                    continue
                neighbourhood = [(r, c)] + self._board.neighbours((r, c))
                share = mass / len(neighbourhood)
                for nr, nc in neighbourhood:
                    new_matrix[nr][nc] += share
                    new_allowed.add((nr, nc))
        self._matrix = new_matrix
        if new_allowed:
            self._allowed = new_allowed
        self._normalize()

    def observe_smell(self, field: dict[str, float]) -> None:
        """Apply scent observation; selected form is fixed at construction (FR-B2)."""
        if self._update_form == "trust_v1":
            from .update import observe_trust

            self._matrix = observe_trust(self._matrix, field, self._trust, self._board.size)
        else:
            from .update import observe_kernel

            self._matrix = observe_kernel(
                self._matrix, field, self._trust, self._board.size, self._probe
            )
        self._normalize()

    def apply_hint(self, hint: str, arena: str) -> None:
        """Delegate to hints module (FR-B5)."""
        from .hints import apply_hint as _apply

        _apply(self, hint, arena, self._board.size, self._hint_reliability)

    def _normalize(self) -> None:
        """Normalize mass over allowed cells. Raises ValueError if no allowed cells remain."""
        for r in range(self._board.size):
            for c in range(self._board.size):
                if (r, c) not in self._allowed or self._matrix[r][c] < 0.0:
                    self._matrix[r][c] = 0.0

        total = sum(sum(row) for row in self._matrix)
        if total <= _EPSILON:
            if not self._allowed:
                raise ValueError("No allowed cells remain on board to normalize")
            uniform_prob = 1.0 / len(self._allowed)
            for r in range(self._board.size):
                for c in range(self._board.size):
                    self._matrix[r][c] = uniform_prob if (r, c) in self._allowed else 0.0
        else:
            for r in range(self._board.size):
                for c in range(self._board.size):
                    self._matrix[r][c] /= total
