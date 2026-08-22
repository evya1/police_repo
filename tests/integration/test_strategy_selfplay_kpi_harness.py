"""KPI harness runner + TC-P22 / TC-P20 / TC-P21 tests (role-pinned Police).

TC-P22 — 20 seeded games, role-pinned Police sub-games, shipped config.
TC-P20 — determinism: two runs, same seed + same wire transcript => identical rows.
TC-P21 — performance: <= 10 ms p99 over 10k iterations, incl. where_place_barrier.

The Police side is built by ``create_peer`` — the production composition root — reading the
shipped ``config/game.json`` with the normal private-config default, so this measures what
the CLI actually ships and not a hand-assembled engine. Only the budgets are swapped, for a
fast in-process loopback.
"""

from __future__ import annotations

import json
import os
import random
import statistics
import subprocess
import sys
import threading
from pathlib import Path

from common.domain.scoring import Outcome, Role
from common.transport.loopback import pair
from common.transport.series import PeerConfig, PeerFacade, SeriesRow
from common.transport.subgame import play_subgame
from police_peer.sdk import create_peer
from tests.integration.test_strategy_selfplay_kpi import (
    DummyBudgets,
    KPIResult,
    UniformRandomThief,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SHIPPED_CONFIG = _REPO_ROOT / "config" / "game.json"
_LATENCY_PROBE = _REPO_ROOT / "tests" / "perf" / "police_latency_probe.py"


def _production_police(channel, seed: int) -> PeerFacade:
    """The Police peer exactly as production composes it, minus the real budgets."""
    return create_peer(
        config_path=_SHIPPED_CONFIG,
        channel=channel,
        role=Role.POLICE,
        seed=seed,
        group_id="Police",
        budgets=DummyBudgets(),
    )


def _play_one_game(i: int, seed: int) -> KPIResult:
    """One cop-pinned sub-game (odd number) over loopback, two worker threads."""
    a, b = pair("Police", "Thief")
    facade = _production_police(a, seed + i)
    police_engine, cfg_a = facade.engine, facade.config
    cfg_b = PeerConfig(Role.THIEF, DummyBudgets(), cfg_a.terms, seed=seed + i)
    thief_engine = UniformRandomThief(random.Random(seed + i + 1000))
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
        barriers_used=police_engine._session.engine.barriers_placed,
        captured=row_a.outcome is Outcome.CAPTURE,
    )


def _run_kpi_games(num_games: int, seed: int) -> list[KPIResult]:
    """Run num_games sub-games with Police always the cop (odd numbers pin the role)."""
    return [_play_one_game(i, seed) for i in range(1, num_games + 1)]


def test_tc_p22_kpi_selfplay() -> None:
    """TC-P22: 20 seeded games, role-pinned Police, production-composed shipped config."""
    results = _run_kpi_games(20, seed=7)
    captures = [r for r in results if r.captured]
    capture_rate = len(captures) / len(results)
    assert capture_rate >= 0.60, (
        f"capture rate {capture_rate:.2%} < 60% "
        f"({len(captures)}/{len(results)})"
    )
    median_rtc = statistics.median(r.steps for r in captures)
    assert median_rtc <= 28, f"median rounds-to-capture {median_rtc} > 28"
    low_barrier = sum(1 for r in captures if r.barriers_used <= 8)
    low_rate = low_barrier / len(captures)
    assert low_rate >= 0.50, (
        f"captures with <=8 barriers {low_rate:.2%} < 50% ({low_barrier}/{len(captures)})"
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


def run_latency_probe() -> dict:
    """Run the measured loop in a clean, uninstrumented child process."""
    env = {
        k: v for k, v in os.environ.items()
        if not k.startswith(("COV_CORE", "COVERAGE", "PYTEST"))
    }
    proc = subprocess.run(  # noqa: S603
        [sys.executable, str(_LATENCY_PROBE)],
        capture_output=True, text=True, env=env, cwd=_REPO_ROOT, timeout=600, check=True,
    )
    return json.loads(proc.stdout)


def test_tc_p21_performance() -> None:
    """TC-P21: <= 10 ms p99 over 10k measured iterations, after a 1k warm-up."""
    sample = run_latency_probe()
    assert sample["warmup"] == 1000 and sample["measured"] == 10000
    assert not sample["traced"], "the measured loop ran under a tracer"
    assert not sample["coverage_imported"], "the measured loop ran under coverage"
    assert sample["p99_ms"] <= 10.0, f"p99 latency {sample['p99_ms']:.2f} ms > 10 ms"
