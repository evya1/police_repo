"""Thread-safe, deadline-aware central Gatekeeper for all external service calls.

One Lock/Condition-protected state machine enforces the active-call count, the
concurrency cap, a bounded waiting queue, the token bucket, the daily quota,
and per-lane reservations so optional LLM traffic never starves reporting.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from collections.abc import Callable
from typing import Any

from police_peer.infra.gatekeeper_types import (
    DailyQuotaExceededError,
    DeadlineExceededError,
    DosLockoutError,
    ExternalCallError,
    GatekeeperConfig,
    GatekeeperError,
    Lane,
    QueueFullError,
    RateGuard,
    RateLimitExceededError,
    can_admit,
    is_lane_head,
    remaining_budget,
)
from police_peer.infra.retry_policy import (
    has_budget_for,
    is_hard_failure,
    is_transient,
    next_backoff,
)

__all__ = [
    "DailyQuotaExceededError",
    "DeadlineExceededError",
    "DosLockoutError",
    "ExternalApiGatekeeper",
    "ExternalCallError",
    "GatekeeperConfig",
    "GatekeeperError",
    "QueueFullError",
    "RateLimitExceededError",
]


class ExternalApiGatekeeper:
    """Central configuration-driven gatekeeper enforcing rate/DoS/quota/lane rules."""

    def __init__(
        self, config: GatekeeperConfig | None = None,
        time_provider: Callable[[], float] = time.time, sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        self.cfg = config or GatekeeperConfig()
        self._time = time_provider
        self._sleep = sleeper
        self._cv = threading.Condition(threading.Lock())
        self._rate = RateGuard(self.cfg, self._time())
        self._active_total = 0
        self._active_lane: dict[Lane, int] = {"reporting": 0, "llm": 0}
        self._wait_queue: deque[tuple[int, Lane]] = deque()
        self._next_ticket_id = 0

    def _ready(self, ticket: int, lane: Lane) -> bool:
        admit = can_admit(self.cfg, lane, self._active_total, self._active_lane)
        return admit and is_lane_head(self._wait_queue, ticket, lane)

    def _wait_for_slot(self, lane: Lane, deadline: float | None) -> None:
        """Block for a permit. A lane rival queued ahead never blocks another lane's admission."""
        if self._ready(-1, lane):
            return
        remaining = remaining_budget(self._time(), deadline)
        if remaining is not None and remaining <= 0:
            raise DeadlineExceededError("Deadline expired before a permit was available.")
        if len(self._wait_queue) >= self.cfg.queue_depth:
            raise QueueFullError("Gatekeeper waiting queue is full.")
        ticket = self._next_ticket_id
        self._next_ticket_id += 1
        entry = (ticket, lane)
        self._wait_queue.append(entry)
        try:
            while not self._ready(ticket, lane):
                remaining = remaining_budget(self._time(), deadline)
                if remaining is not None and remaining <= 0:
                    raise DeadlineExceededError("Deadline expired while waiting for a permit.")
                self._cv.wait(timeout=remaining)
            self._wait_queue.remove(entry)
        except Exception:
            if entry in self._wait_queue:
                self._wait_queue.remove(entry)
                self._cv.notify_all()
            raise

    def acquire_permission(self, lane: Lane = "reporting", deadline: float | None = None) -> None:
        """Reserve one permit in `lane`, queueing until available or `deadline` expires."""
        with self._cv:
            now = self._time()
            self._rate.check_dos(now)
            self._rate.check_daily_quota(now)
            self._rate.refill(now)
            if self._rate.tokens < 1.0:
                raise RateLimitExceededError("Rate limit exceeded; token bucket is empty.")
            self._wait_for_slot(lane, deadline)
            self._rate.consume()
            self._active_total += 1
            self._active_lane[lane] += 1

    def _release(self, lane: Lane) -> None:
        with self._cv:
            self._active_total -= 1
            self._active_lane[lane] -= 1
            self._cv.notify_all()

    def execute(
        self, call: Callable[..., Any], *args: Any,
        lane: Lane = "reporting", deadline: float | None = None, **kwargs: Any,
    ) -> Any:
        """Execute an external call behind the Gatekeeper's rate/DoS/lane guards and 429 retry."""
        self.acquire_permission(lane, deadline)
        try:
            return self._call_with_retry(call, args, kwargs, deadline)
        finally:
            self._release(lane)

    def _call_with_retry(
        self, call: Callable[..., Any], args: tuple[Any, ...], kwargs: dict[str, Any], deadline: float | None,
    ) -> Any:
        retries = 0
        backoff = self.cfg.retry_backoff_sec
        while True:
            try:
                return call(*args, **kwargs)
            except GatekeeperError:
                raise
            except Exception as exc:
                if is_hard_failure(exc):
                    raise
                if not is_transient(exc) or retries >= self.cfg.max_retries:
                    raise ExternalCallError(f"External call failed: {exc}") from exc
                remaining = remaining_budget(self._time(), deadline)
                if not has_budget_for(remaining, backoff):
                    raise DeadlineExceededError(
                        "Deadline would be exceeded by the next retry backoff."
                    ) from exc
                retries += 1
                self._sleep(backoff)
                backoff = next_backoff(backoff)

    def get_stats(self) -> dict[str, Any]:
        with self._cv:
            now = self._time()
            self._rate.refill(now)
            return {
                "available_tokens": self._rate.tokens,
                "daily_requests_used": self._rate.daily_count,
                "is_locked_out": self._rate.is_locked_out(now),
                "active_calls": self._active_total,
                "active_by_lane": dict(self._active_lane),
                "waiting_count": len(self._wait_queue),
            }
