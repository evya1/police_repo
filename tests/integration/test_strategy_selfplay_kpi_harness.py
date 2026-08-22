"""KPI harness runner + TC-P22 / TC-P20 / TC-P21 tests (role-pinned Police).

TC-P22 — 20 seeded games, role-pinned Police sub-games, shipped config.
TC-P20 — determinism: two runs, same seed + same wire transcript => identical rows.
TC-P21 — performance: <= 10 ms p99 over 10k iterations, incl. where_place_barrier.
"""

from __future__ import annotations

import random
import statistics
import threading
import time

from common.domain.board import Board
from common.domain.rules import GameEngine
from common.domain.scoring import Outcome, Role
from common.transport.loopback import pair
from common.transport.series import PeerConfig, SeriesRow
from common.transport.subgame import play_subgame
from police_peer.wire import BrainDrivenEngine
from src.police_peer.strategy.barriers import where_place_barrier
from tests.integration.test_strategy_selfplay_kpi import (
    DummyBudgets,
    KPIResult,
    RandomThiefEngine,
    _terms,
)


def _play_one_game(i: int, seed: int) -> KPIResult:
    """One cop-pinned sub-game (odd number) over loopback, two worker threads."""
    a, b = pair("Police", "Thief")
    cfg_a = PeerConfig(Role.POLICE, DummyBudgets(), _terms, seed=seed + i)
    cfg_b = PeerConfig(Role.THIEF, DummyBudgets(), _terms, seed=seed + i)
    police_engine = BrainDrivenEngine(Role.POLICE, seed=seed + i, config={})
    thief_engine = RandomThiefEngine(random.Random(seed + i + 1000))
    row_a: SeriesRow | None = None
    errors: list[Exception] = []

    def run_a() -> None:
        nonlocal row_a
        try:
            row_a = play_subgame(a, police_engine, cfg_a, 2 * i - 1)
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    def run_b() -> None:
        try:
            play_subgame(b, thief_engine, cfg_b, 2 * i - 1)
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    thread_a = threading.Thread(target=run_a, daemon=True)
    thread_b = threading.Thread(target=run_b, daemon=True)
    thread_a.start()
    thread_b.start()
    thread_a.join(timeout=120)
    thread_b.join(timeout=120)
    if thread_a.is_alive() or thread_b.is_alive():
        raise TimeoutError("kpi series worker timed out / stuck")
    if errors:
        raise RuntimeError(f"kpi series errors: {errors}")
    return KPIResult(
        sub_game=2 * i - 1,
        outcome=row_a.outcome,
        steps=row_a.steps,
        barriers_used=police_engine._engine.barriers_placed,
        captured=row_a.outcome is Outcome.CAPTURE,
    )


def _run_kpi_games(num_games: int, seed: int) -> list[KPIResult]:
    """Run num_games sub-games with Police always the cop (odd numbers pin the role)."""
    return [_play_one_game(i, seed) for i in range(1, num_games + 1)]


def test_tc_p22_kpi_selfplay() -> None:
    """TC-P22: 20 seeded games, role-pinned Police, shipped config."""
    results = _run_kpi_games(20, seed=7)
    captures = [r for r in results if r.captured]
    capture_rate = len(captures) / len(results)
    assert capture_rate >= 0.60, (
        f"capture rate {capture_rate:.2%} < 60% "
        f"({len(captures)}/{len(results)})"
    )
    if captures:
        median_rtc = statistics.median(r.steps for r in captures)
        assert median_rtc <= 28, f"median rounds-to-capture {median_rtc} > 28"
        low_barrier = sum(1 for r in captures if r.barriers_used <= 8)
        low_rate = low_barrier / len(captures)
        assert low_rate >= 0.50, (
            f"captures with <=8 barriers {low_rate:.2%} < 50% "
            f"({low_barrier}/{len(captures)})"
        )
    for r in results:
        assert r.outcome in (Outcome.CAPTURE, Outcome.SURVIVAL), (
            f"unexpected outcome {r.outcome} in sub-game {r.sub_game}"
        )


def test_tc_p20_determinism() -> None:
    """TC-P20: two runs, same seed + same wire transcript => identical rows."""
    results1 = _run_kpi_games(20, seed=99)
    results2 = _run_kpi_games(20, seed=99)
    assert len(results1) == len(results2)
    for r1, r2 in zip(results1, results2, strict=True):
        assert r1.outcome == r2.outcome, (
            f"sub-game {r1.sub_game}: outcome mismatch {r1.outcome} vs {r2.outcome}"
        )
        assert r1.steps == r2.steps, f"sub-game {r1.sub_game}: steps mismatch"
        assert r1.barriers_used == r2.barriers_used, (
            f"sub-game {r1.sub_game}: barriers mismatch"
        )


def test_tc_p21_performance() -> None:
    """TC-P21: <= 10 ms p99 over 10k iterations, including where_place_barrier."""
    engine = GameEngine(board=Board(size=7), role=Role.POLICE, position=(3, 3))

    class _Belief:
        def __init__(self):
            self._peak = (5, 5)

        def most_likely(self):
            return self._peak

        def peak_probability(self) -> float:
            return 0.5

        def prob(self, cell):
            return 0.5 if cell == self._peak else 0.01

    belief = _Belief()
    cfg: dict[str, object] = {
        "barrier_mass_floor": 0.05,
        "w_mass": 1.0,
        "w_cut": 0.5,
        "route_slack": 1,
        "barrier_reserve": 3,
        "strong_threshold": 0.8,
        "barrier_score_threshold": 0.3,
    }
    times: list[float] = []
    n = 10_000
    for _ in range(n):
        start = time.perf_counter()
        where_place_barrier(engine, belief, cfg)
        times.append(time.perf_counter() - start)
    times.sort()
    p99_ms = times[int(n * 0.99)] * 1000
    assert p99_ms <= 10.0, f"p99 latency {p99_ms:.2f} ms > 10 ms"
