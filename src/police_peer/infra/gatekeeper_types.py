"""Typed configuration, lane identifiers, and error hierarchy for the Gatekeeper.

Split out of `external_api_gatekeeper.py` so the stateful coordinator stays under
the repository line cap. Nothing here owns mutable state.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Literal

Lane = Literal["reporting", "llm"]
"""The two service lanes inside the single Gatekeeper instance."""


class GatekeeperError(Exception):
    """Base error for Gatekeeper violations."""


class RateLimitExceededError(GatekeeperError):
    """Raised when the rate limit token bucket is exhausted."""


class DosLockoutError(GatekeeperError):
    """Raised when rapid requests trigger a DoS lockout."""


class DailyQuotaExceededError(GatekeeperError):
    """Raised when the daily quota is exceeded."""


class QueueFullError(GatekeeperError):
    """Raised when the bounded waiting queue is genuinely at capacity."""


class DeadlineExceededError(GatekeeperError):
    """Raised when the caller-supplied deadline cannot be honoured."""


class ExternalCallError(GatekeeperError):
    """Raised when an external call fails after exhausting retries."""


@dataclass
class GatekeeperConfig:
    """Conservative, override-friendly limits for the central Gatekeeper.

    `concurrent_requests` bounds simultaneous in-flight calls across both lanes.
    `reporting_reserved_slots` is capacity the `llm` lane may never consume, so
    mandatory reporting always has room even when `llm` traffic is saturated.
    `queue_depth` bounds how many callers may wait for a permit at once.
    """

    requests_per_minute: int = 30
    bucket_capacity: int = 30
    concurrent_requests: int = 2
    queue_depth: int = 100
    max_retries: int = 3
    retry_backoff_sec: float = 0.5
    dos_threshold: int = 15
    dos_window_sec: float = 2.0
    dos_lockout_sec: float = 10.0
    daily_quota: int = 1000
    reporting_reserved_slots: int = 1

    def llm_max_concurrent(self) -> int:
        """Return the hard cap on simultaneous `llm`-lane calls."""
        return max(0, self.concurrent_requests - self.reporting_reserved_slots)


def remaining_budget(now: float, deadline: float | None) -> float | None:
    """Return seconds left before `deadline`, or None when no deadline applies."""
    if deadline is None:
        return None
    return deadline - now


def can_admit(cfg: GatekeeperConfig, lane: Lane, active_total: int, active_lane: dict[Lane, int]) -> bool:
    """True when one more `lane` call may start given the global cap and lane reservation."""
    if active_total >= cfg.concurrent_requests:
        return False
    return not (lane == "llm" and active_lane["llm"] >= cfg.llm_max_concurrent())


def is_lane_head(wait_queue: deque[tuple[int, Lane]], ticket: int, lane: Lane) -> bool:
    """True when `ticket` is the earliest queued ticket in `lane` (per-lane FIFO).

    Queue discipline is FIFO *within each lane*, not globally: a waiting `llm`
    ticket must never block an admissible `reporting` ticket queued behind it.
    """
    lane_tickets = [t for t, waiting_lane in wait_queue if waiting_lane == lane]
    return not lane_tickets or ticket == min(lane_tickets)


class RateGuard:
    """Owns the token bucket, DoS window, and daily quota (no lane/concurrency logic)."""

    def __init__(self, cfg: GatekeeperConfig, now: float) -> None:
        self.cfg = cfg
        self.tokens = float(cfg.bucket_capacity)
        self.daily_count = 0
        self._last_refill = now
        self._lockout_until = 0.0
        self._history: deque[float] = deque()
        self._daily_reset_time = now + 86400.0

    def is_locked_out(self, now: float) -> bool:
        return now < self._lockout_until

    def refill(self, now: float) -> None:
        elapsed = now - self._last_refill
        if elapsed > 0:
            refill = elapsed * (self.cfg.requests_per_minute / 60.0)
            self.tokens = min(float(self.cfg.bucket_capacity), self.tokens + refill)
            self._last_refill = now

    def check_dos(self, now: float) -> None:
        if now < self._lockout_until:
            remaining = self._lockout_until - now
            raise DosLockoutError(f"Gatekeeper in DoS lockout. Remaining: {remaining:.1f}s")
        while self._history and (now - self._history[0]) > self.cfg.dos_window_sec:
            self._history.popleft()
        if len(self._history) >= self.cfg.dos_threshold:
            self._lockout_until = now + self.cfg.dos_lockout_sec
            raise DosLockoutError(
                f"DoS threshold hit ({len(self._history)} reqs in "
                f"{self.cfg.dos_window_sec}s). Lockout activated."
            )
        self._history.append(now)

    def check_daily_quota(self, now: float) -> None:
        if now >= self._daily_reset_time:
            self.daily_count = 0
            self._daily_reset_time = now + 86400.0
        if self.daily_count >= self.cfg.daily_quota:
            raise DailyQuotaExceededError(f"Daily quota of {self.cfg.daily_quota} operations exceeded.")

    def consume(self) -> None:
        """Decrement one token and count one request. Call only after check_* pass."""
        self.tokens -= 1.0
        self.daily_count += 1
