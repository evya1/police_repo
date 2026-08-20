from __future__ import annotations

import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


class GatekeeperError(Exception):
    """Base error for Gatekeeper violations."""


class RateLimitExceededError(GatekeeperError):
    """Raised when the rate limit token bucket is exhausted."""


class DosLockoutError(GatekeeperError):
    """Raised when rapid requests trigger a DoS lockout."""


class DailyQuotaExceededError(GatekeeperError):
    """Raised when daily quota is exceeded."""


class QueueFullError(GatekeeperError):
    """Raised when pending request queue depth exceeds capacity."""


class ExternalCallError(GatekeeperError):
    """Raised when external call fails after max retries."""


@dataclass
class GatekeeperConfig:
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


class ExternalApiGatekeeper:
    """Central configuration-driven gatekeeper enforcing rate limits, DoS locks, and 429 backoffs."""

    def __init__(self, config: GatekeeperConfig | None = None, time_provider: Callable[[], float] = time.time) -> None:
        self.cfg = config or GatekeeperConfig()
        self._time = time_provider
        self._tokens = float(self.cfg.bucket_capacity)
        self._last_refill = self._time()
        self._lockout_until = 0.0
        self._request_history: deque[float] = deque()
        self._daily_count = 0
        self._daily_reset_time = self._time() + 86400.0
        self._active_calls = 0

    def _refill_tokens(self, now: float) -> None:
        elapsed = now - self._last_refill
        if elapsed > 0:
            refill = elapsed * (self.cfg.requests_per_minute / 60.0)
            self._tokens = min(float(self.cfg.bucket_capacity), self._tokens + refill)
            self._last_refill = now

    def _check_dos(self, now: float) -> None:
        if now < self._lockout_until:
            remaining = self._lockout_until - now
            raise DosLockoutError(f"Gatekeeper in DoS lockout. Remaining: {remaining:.1f}s")
        # Prune older than dos_window
        while self._request_history and (now - self._request_history[0]) > self.cfg.dos_window_sec:
            self._request_history.popleft()
        if len(self._request_history) >= self.cfg.dos_threshold:
            self._lockout_until = now + self.cfg.dos_lockout_sec
            raise DosLockoutError(f"DoS threshold hit ({len(self._request_history)} reqs in {self.cfg.dos_window_sec}s). Lockout activated.")
        self._request_history.append(now)

    def _check_daily_quota(self, now: float) -> None:
        if now >= self._daily_reset_time:
            self._daily_count = 0
            self._daily_reset_time = now + 86400.0
        if self._daily_count >= self.cfg.daily_quota:
            raise DailyQuotaExceededError(f"Daily quota of {self.cfg.daily_quota} operations exceeded.")

    def acquire_permission(self) -> None:
        now = self._time()
        self._check_dos(now)
        self._check_daily_quota(now)
        self._refill_tokens(now)

        if self._tokens < 1.0:
            raise RateLimitExceededError("Rate limit exceeded; token bucket is empty.")
        if self._active_calls >= self.cfg.queue_depth:
            raise QueueFullError("Gatekeeper queue is full.")

        self._tokens -= 1.0
        self._daily_count += 1

    def execute(self, call: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute external service call behind Token Bucket, DoS guard, and 429 retry backoff."""
        self.acquire_permission()
        self._active_calls += 1
        retries = 0
        backoff = self.cfg.retry_backoff_sec

        try:
            while True:
                try:
                    return call(*args, **kwargs)
                except Exception as exc:
                    status_code = getattr(exc, "status_code", None) or getattr(exc, "code", None)
                    is_429 = status_code == 429 or "429" in str(exc) or "rate" in str(exc).lower()
                    if is_429 and retries < self.cfg.max_retries:
                        retries += 1
                        time.sleep(backoff)
                        backoff *= 2.0
                        continue
                    raise ExternalCallError(f"External call failed: {exc}") from exc
        finally:
            self._active_calls -= 1

    def get_stats(self) -> dict[str, Any]:
        now = self._time()
        self._refill_tokens(now)
        return {
            "available_tokens": self._tokens,
            "daily_requests_used": self._daily_count,
            "is_locked_out": now < self._lockout_until,
            "active_calls": self._active_calls,
        }
