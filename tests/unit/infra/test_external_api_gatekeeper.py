import pytest

from police_peer.infra.external_api_gatekeeper import (
    DailyQuotaExceededError,
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


def test_token_bucket_rate_limiter():
    clock = FakeClock()
    cfg = GatekeeperConfig(requests_per_minute=60, bucket_capacity=2, dos_threshold=100)
    gk = ExternalApiGatekeeper(config=cfg, time_provider=clock)

    # Consume available tokens
    assert gk.execute(lambda: "call1") == "call1"
    assert gk.execute(lambda: "call2") == "call2"

    # Bucket exhausted
    with pytest.raises(RateLimitExceededError):
        gk.execute(lambda: "call3")

    # Advance clock 1 second -> 1 token refilled (60/min = 1/s)
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

    # 4th request within dos window triggers lockout
    with pytest.raises(DosLockoutError):
        gk.execute(lambda: 4)

    # Still locked out after 5s
    clock.advance(5.0)
    with pytest.raises(DosLockoutError):
        gk.execute(lambda: 5)

    # Lockout expires after 10.1s total
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
            err = Exception("429 Too Many Requests")
            setattr(err, "status_code", 429)
            raise err
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
