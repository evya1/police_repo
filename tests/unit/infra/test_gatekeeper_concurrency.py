from __future__ import annotations

import threading
import time

from police_peer.infra.external_api_gatekeeper import (
    DeadlineExceededError,
    ExternalApiGatekeeper,
    QueueFullError,
)
from police_peer.infra.gatekeeper_types import GatekeeperConfig


def _spin_until(predicate, timeout: float = 5.0) -> None:
    """Busy-wait (no sleep) for a test-setup condition, bounded by a real-time safety net."""
    deadline = time.monotonic() + timeout
    while not predicate():
        if time.monotonic() > deadline:
            raise AssertionError("condition not met before timeout")


def test_max_concurrency_enforced() -> None:
    """No more than `concurrent_requests` calls run at once, across N contenders."""
    cfg = GatekeeperConfig(concurrent_requests=2, queue_depth=10, bucket_capacity=1000, dos_threshold=1000, daily_quota=1000, reporting_reserved_slots=0, requests_per_minute=6000)
    gk = ExternalApiGatekeeper(config=cfg, sleeper=lambda s: None)
    active = 0
    max_active = 0
    state_lock = threading.Lock()
    hold_event = threading.Event()

    def call_fn():
        nonlocal active, max_active
        with state_lock:
            active += 1
            max_active = max(max_active, active)
        hold_event.wait(timeout=5)
        with state_lock:
            active -= 1
        return "ok"

    threads = [threading.Thread(target=gk.execute, args=(call_fn,), kwargs={"lane": "llm"}) for _ in range(5)]
    for t in threads:
        t.start()

    # Spin (no sleep) until exactly `concurrent_requests` calls have been admitted.
    _spin_until(lambda: gk.get_stats()["active_calls"] == cfg.concurrent_requests)
    with state_lock:
        assert active == cfg.concurrent_requests
        assert max_active == cfg.concurrent_requests
    hold_event.set()
    for t in threads:
        t.join(timeout=5)
    assert max_active == cfg.concurrent_requests


def test_fifo_queue_discipline() -> None:
    """Callers queued behind a saturated lane are admitted in strict arrival order."""
    cfg = GatekeeperConfig(concurrent_requests=1, queue_depth=5, bucket_capacity=1000, dos_threshold=1000, daily_quota=1000, reporting_reserved_slots=0, requests_per_minute=6000)
    gk = ExternalApiGatekeeper(config=cfg, sleeper=lambda s: None)
    hold_first = threading.Event()
    order: list[int] = []
    order_lock = threading.Lock()

    def blocker():
        gk.execute(lambda: hold_first.wait(timeout=5), lane="llm")

    t0 = threading.Thread(target=blocker)
    t0.start()
    _spin_until(lambda: gk.get_stats()["active_calls"] == 1)

    def waiter(i: int):
        def call_fn():
            with order_lock:
                order.append(i)
            return i

        gk.execute(call_fn, lane="llm")

    threads = []
    for i in range(3):
        th = threading.Thread(target=waiter, args=(i,))
        threads.append(th)
        th.start()
        _spin_until(lambda n=i: gk.get_stats()["waiting_count"] == n + 1)

    hold_first.set()
    t0.join(timeout=5)
    for th in threads:
        th.join(timeout=5)

    assert order == [0, 1, 2]


def test_reporting_reservation_under_llm_saturation() -> None:
    """Uncontended case: a saturated `llm` lane never consumes the `reporting` reservation."""
    cfg = GatekeeperConfig(concurrent_requests=2, reporting_reserved_slots=1, queue_depth=5, bucket_capacity=1000, dos_threshold=1000, daily_quota=1000, requests_per_minute=6000)
    gk = ExternalApiGatekeeper(config=cfg, sleeper=lambda s: None)
    hold = threading.Event()

    t = threading.Thread(target=lambda: gk.execute(lambda: hold.wait(timeout=5), lane="llm"))
    t.start()
    _spin_until(lambda: gk.get_stats()["active_by_lane"]["llm"] == cfg.llm_max_concurrent())
    assert gk.get_stats()["waiting_count"] == 0  # reporting never had to queue behind anything

    result = gk.execute(lambda: "reporting-ok", lane="reporting")
    assert result == "reporting-ok"

    hold.set()
    t.join(timeout=5)


def test_reporting_bypasses_queued_llm_head_under_load() -> None:
    """Contended: llm B queues behind saturated llm A; reporting C, arriving after B,
    must still be admitted promptly — a queued llm ticket must never block it."""
    cfg = GatekeeperConfig(concurrent_requests=2, reporting_reserved_slots=1, queue_depth=5, bucket_capacity=1000, dos_threshold=1000, daily_quota=1000, requests_per_minute=6000)
    gk = ExternalApiGatekeeper(config=cfg, sleeper=lambda s: None)
    hold = threading.Event()

    t_a = threading.Thread(target=lambda: gk.execute(lambda: hold.wait(timeout=5), lane="llm"))
    t_a.start()
    _spin_until(lambda: gk.get_stats()["active_by_lane"]["llm"] == cfg.llm_max_concurrent())

    t_b = threading.Thread(target=lambda: gk.execute(lambda: hold.wait(timeout=5), lane="llm"))
    t_b.start()
    _spin_until(lambda: gk.get_stats()["waiting_count"] == 1)

    reporting_done = threading.Event()

    def reporting_call():
        gk.execute(lambda: "reporting-ok", lane="reporting")
        reporting_done.set()

    t_c = threading.Thread(target=reporting_call)
    t_c.start()

    # Bounded to 1s (well under A/B's 5s hold): C must not be starved behind B's llm ticket.
    _spin_until(reporting_done.is_set, timeout=1.0)
    t_c.join(timeout=5)

    hold.set()
    t_a.join(timeout=5)
    t_b.join(timeout=5)


def test_queue_full_only_at_real_capacity() -> None:
    """QueueFull fires only once the bounded waiting count is truly exhausted."""
    cfg = GatekeeperConfig(concurrent_requests=1, queue_depth=1, bucket_capacity=1000, dos_threshold=1000, daily_quota=1000, reporting_reserved_slots=0, requests_per_minute=6000)
    gk = ExternalApiGatekeeper(config=cfg, sleeper=lambda s: None)
    hold = threading.Event()

    t0 = threading.Thread(target=lambda: gk.execute(lambda: hold.wait(timeout=5), lane="llm"))
    t0.start()
    _spin_until(lambda: gk.get_stats()["active_calls"] == 1)

    t1 = threading.Thread(target=lambda: gk.execute(lambda: hold.wait(timeout=5), lane="llm"))
    t1.start()
    _spin_until(lambda: gk.get_stats()["waiting_count"] == 1)  # fills the single waiting slot

    try:
        gk.execute(lambda: "unreachable", lane="llm")
        raise AssertionError("expected QueueFullError")
    except QueueFullError:
        pass

    hold.set()
    t0.join(timeout=5)
    t1.join(timeout=5)


def test_no_leaked_permits_on_deadline_expiry() -> None:
    """A queued caller whose deadline expires must not leave a stuck waiter behind."""
    cfg = GatekeeperConfig(concurrent_requests=1, queue_depth=5, bucket_capacity=1000, dos_threshold=1000, daily_quota=1000, reporting_reserved_slots=0, requests_per_minute=6000)
    gk = ExternalApiGatekeeper(config=cfg, sleeper=lambda s: None)
    hold = threading.Event()

    t0 = threading.Thread(target=lambda: gk.execute(lambda: hold.wait(timeout=5), lane="llm"))
    t0.start()
    _spin_until(lambda: gk.get_stats()["active_calls"] == 1)

    deadline = time.time() + 0.05  # same clock family as the gatekeeper's default time_provider
    try:
        gk.execute(lambda: "unreachable", lane="llm", deadline=deadline)
        raise AssertionError("expected DeadlineExceededError")
    except DeadlineExceededError:
        pass

    _spin_until(lambda: gk.get_stats()["waiting_count"] == 0)

    hold.set()
    t0.join(timeout=5)
    assert gk.get_stats()["active_calls"] == 0
    assert gk.get_stats()["waiting_count"] == 0
