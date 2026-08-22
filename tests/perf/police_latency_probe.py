"""TC-P21 measured loop, isolated from the coverage-instrumented test process.

Run as a script; it prints one JSON object on stdout. It is deliberately NOT a
``test_*`` module: pytest never collects it, so the numbers it reports are the
production cost of ``where_place_barrier`` and not the cost of tracing it.
"""

from __future__ import annotations

import json
import sys
import time

from common.domain.board import Board
from common.domain.rules import GameEngine
from common.domain.scoring import Role
from police_peer.strategy.barriers import where_place_barrier

WARMUP_ITERATIONS = 1_000
MEASURED_ITERATIONS = 10_000

#: The shipped defaults ``resolve_brain`` hands the barrier planner.
BARRIER_CONFIG: dict[str, object] = {
    "barrier_mass_floor": 0.05,
    "w_mass": 1.0,
    "w_cut": 0.5,
    "route_slack": 1,
    "barrier_reserve": 3,
    "strong_threshold": 0.8,
    "barrier_score_threshold": 0.3,
}


class _PeakedBelief:
    """A fixed belief peak — the planner's input, held constant across iterations."""

    def __init__(self, peak: tuple[int, int] = (5, 5)) -> None:
        self._peak = peak

    def most_likely(self) -> tuple[int, int]:
        return self._peak

    def peak_probability(self) -> float:
        return 0.5

    def prob(self, cell: tuple[int, int]) -> float:
        return 0.5 if cell == self._peak else 0.01


def measure(
    warmup: int = WARMUP_ITERATIONS, measured: int = MEASURED_ITERATIONS,
) -> dict[str, object]:
    """Warm up, then time ``measured`` calls and report the p99 in milliseconds."""
    engine = GameEngine(board=Board(size=7), role=Role.POLICE, position=(3, 3))
    belief = _PeakedBelief()
    for _ in range(warmup):
        where_place_barrier(engine, belief, BARRIER_CONFIG)

    times: list[float] = []
    for _ in range(measured):
        start = time.perf_counter()
        where_place_barrier(engine, belief, BARRIER_CONFIG)
        times.append(time.perf_counter() - start)
    times.sort()
    return {
        "warmup": warmup,
        "measured": measured,
        "p99_ms": times[int(measured * 0.99)] * 1000.0,
        "max_ms": times[-1] * 1000.0,
        "median_ms": times[measured // 2] * 1000.0,
        # Proof the sample is uninstrumented: no tracer, and coverage never imported.
        "traced": sys.gettrace() is not None,
        "coverage_imported": "coverage" in sys.modules,
    }


if __name__ == "__main__":
    json.dump(measure(), sys.stdout)
