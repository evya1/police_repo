"""Drive both ends of one channel through a full series (harness, not the engine).

Split out of ``series.py``: that module owns the per-peer engine (``PeerFacade``) and the
value types a series produces, while this one owns the two-peer *harness* -- the threads,
the join deadlines, and the error aggregation that let a single process play both sides
over a loopback pair. Production runs one peer per OS process and never calls this; it is
the in-process path CI uses to exercise a whole series deterministically.
"""

from __future__ import annotations

import threading

from common.transport.replay_evidence import SubgameDriver
from common.transport.series import PeerConfig, PeerFacade, SeriesResult, TurnEngine


def run_series(
    channel_a,
    channel_b,
    config_a: PeerConfig,
    config_b: PeerConfig,
    engine_a: TurnEngine,
    engine_b: TurnEngine,
    subgame_driver: SubgameDriver | None = None,
) -> tuple[SeriesResult, SeriesResult]:
    """Run a series with two peers on opposite ends of a channel. Returns (a, b)."""
    facade_a = PeerFacade(channel_a, engine_a, config_a, "A", subgame_driver=subgame_driver)
    facade_b = PeerFacade(channel_b, engine_b, config_b, "B", subgame_driver=subgame_driver)
    results: list[SeriesResult | None] = [None, None]
    errors: list[Exception] = []

    def run_a() -> None:
        try:
            results[0] = facade_a.run()
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    def run_b() -> None:
        try:
            results[1] = facade_b.run()
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    thread_a = threading.Thread(target=run_a, daemon=True)
    thread_b = threading.Thread(target=run_b, daemon=True)
    thread_a.start()
    thread_b.start()
    thread_a.join(timeout=60)
    thread_b.join(timeout=60)
    if thread_a.is_alive() or thread_b.is_alive():
        raise TimeoutError("series worker timed out / stuck")
    if errors:
        raise RuntimeError(f"series errors: {errors}")
    result_a, result_b = results
    if result_a is None or result_b is None:
        raise RuntimeError("series worker returned no result")
    return result_a, result_b
