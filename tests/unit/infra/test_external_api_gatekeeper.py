import pytest

from police_peer.infra.external_api_gatekeeper import (
    DailyQuotaExceededError,
    DeadlineExceededError,
    DosLockoutError,
    ExternalApiGatekeeper,
    ExternalCallError,
    GatekeeperConfig,
    RateLimitExceededError,
)


class FakeClock:
    def __init__(self, start: float = 1000.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class Http429Error(Exception):
    def __init__(self, msg: str = "429 Too Many Requests"):
        super().__init__(msg)
        self.status_code = 429


def test_token_bucket_rate_limiter():
    clock = FakeClock()
    cfg = GatekeeperConfig(requests_per_minute=60, bucket_capacity=2, dos_threshold=100)
    gk = ExternalApiGatekeeper(config=cfg, time_provider=clock)

    assert gk.execute(lambda: "call1") == "call1"
    assert gk.execute(lambda: "call2") == "call2"

    with pytest.raises(RateLimitExceededError):
        gk.execute(lambda: "call3")

    clock.advance(1.0)
    assert gk.execute(lambda: "call3") == "call3"


def test_dos_lockout_trigger():
    clock = FakeClock()
    cfg = GatekeeperConfig(
        requests_per_minute=600, bucket_capacity=100,
        dos_threshold=3, dos_window_sec=2.0, dos_lockout_sec=10.0,
    )
    gk = ExternalApiGatekeeper(config=cfg, time_provider=clock)

    gk.execute(lambda: 1)
    gk.execute(lambda: 2)
    gk.execute(lambda: 3)

    with pytest.raises(DosLockoutError):
        gk.execute(lambda: 4)

    clock.advance(5.0)
    with pytest.raises(DosLockoutError):
        gk.execute(lambda: 5)

    clock.advance(5.1)
    assert gk.execute(lambda: "recovered") == "recovered"


def test_daily_quota():
    clock = FakeClock()
    cfg = GatekeeperConfig(bucket_capacity=10, daily_quota=2, dos_threshold=100)
    gk = ExternalApiGatekeeper(config=cfg, time_provider=clock)

    gk.execute(lambda: 1)
    gk.execute(lambda: 2)

    with pytest.raises(DailyQuotaExceededError):
        gk.execute(lambda: 3)


def test_retry_on_429():
    clock = FakeClock()
    cfg = GatekeeperConfig(bucket_capacity=10, max_retries=2, retry_backoff_sec=0.01)
    gk = ExternalApiGatekeeper(config=cfg, time_provider=clock)

    attempts = 0

    def flaky_service():
        nonlocal attempts
        attempts += 1
        if attempts < 2:
            raise Http429Error()
        return "success"

    assert gk.execute(flaky_service) == "success"
    assert attempts == 2


def test_max_retries_exceeded():
    cfg = GatekeeperConfig(bucket_capacity=10, max_retries=1, retry_backoff_sec=0.01)
    gk = ExternalApiGatekeeper(config=cfg)

    def bad_service():
        raise Exception("500 Server Error")

    with pytest.raises(ExternalCallError):
        gk.execute(bad_service)


def test_daily_quota_resets_after_window():
    clock = FakeClock()
    cfg = GatekeeperConfig(bucket_capacity=10, daily_quota=1, dos_threshold=100)
    gk = ExternalApiGatekeeper(config=cfg, time_provider=clock)

    gk.execute(lambda: 1)
    with pytest.raises(DailyQuotaExceededError):
        gk.execute(lambda: 2)

    clock.advance(86400.1)
    assert gk.execute(lambda: 3) == 3


def test_deadline_exceeded_fails_fast_no_real_wait():
    """A deadline already in the past must fail immediately, without blocking."""
    clock = FakeClock()
    cfg = GatekeeperConfig(concurrent_requests=1, queue_depth=5, bucket_capacity=100, dos_threshold=100)
    gk = ExternalApiGatekeeper(config=cfg, time_provider=clock)

    gk.acquire_permission(lane="reporting")  # occupy the only permit; never released

    with pytest.raises(DeadlineExceededError):
        gk.execute(lambda: "must not run", lane="reporting", deadline=clock.now - 1.0)


def test_retry_respects_deadline_budget():
    clock = FakeClock()

    def fake_sleep(seconds: float) -> None:
        clock.advance(seconds)

    cfg = GatekeeperConfig(bucket_capacity=10, max_retries=5, retry_backoff_sec=1.0, dos_threshold=100)
    gk = ExternalApiGatekeeper(config=cfg, time_provider=clock, sleeper=fake_sleep)

    attempts = 0

    def flaky_service():
        nonlocal attempts
        attempts += 1
        raise Http429Error()

    deadline = clock.now + 1.5  # enough for one 1.0s backoff, not for the next 2.0s one
    with pytest.raises(DeadlineExceededError):
        gk.execute(flaky_service, deadline=deadline)
    assert attempts == 2


def test_no_leak_on_exception():
    cfg = GatekeeperConfig(bucket_capacity=10, dos_threshold=100, max_retries=0)
    gk = ExternalApiGatekeeper(config=cfg)

    def boom():
        raise ValueError("boom")

    with pytest.raises(ExternalCallError):
        gk.execute(boom, lane="llm")

    stats = gk.get_stats()
    assert stats["active_calls"] == 0
    assert stats["active_by_lane"] == {"reporting": 0, "llm": 0}
    assert stats["waiting_count"] == 0
