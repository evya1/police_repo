from __future__ import annotations

from police_peer.infra.retry_policy import (
    has_budget_for,
    is_hard_failure,
    is_transient,
    next_backoff,
)


class Http429Error(Exception):
    def __init__(self, msg: str = "429 Too Many Requests") -> None:
        super().__init__(msg)
        self.status_code = 429


class DraftSubstitutionError(Exception):
    """Mirrors police_peer.reporting.gmail.DraftSubstitutionError by class name only."""


def test_is_hard_failure_by_class_name() -> None:
    assert is_hard_failure(DraftSubstitutionError("nope")) is True
    assert is_hard_failure(ValueError("nope")) is False


def test_is_transient_status_code() -> None:
    assert is_transient(Http429Error()) is True


def test_is_transient_message_signature() -> None:
    assert is_transient(Exception("429 rate limited")) is True
    assert is_transient(Exception("Rate limit hit")) is True
    assert is_transient(Exception("boom")) is False


def test_is_transient_ignores_non_429_status_code() -> None:
    exc = Exception("Internal Server Error")
    exc.status_code = 500  # type: ignore[attr-defined]
    assert is_transient(exc) is False


def test_next_backoff_doubles_by_default() -> None:
    assert next_backoff(0.5) == 1.0
    assert next_backoff(1.0) == 2.0


def test_next_backoff_custom_multiplier() -> None:
    assert next_backoff(1.0, multiplier=3.0) == 3.0


def test_has_budget_for_no_deadline_always_true() -> None:
    assert has_budget_for(None, needed=999.0) is True


def test_has_budget_for_enough_remaining() -> None:
    assert has_budget_for(remaining=2.0, needed=1.0) is True
    assert has_budget_for(remaining=1.0, needed=1.0) is True


def test_has_budget_for_insufficient_remaining() -> None:
    assert has_budget_for(remaining=0.5, needed=1.0) is False
    assert has_budget_for(remaining=0.0, needed=0.1) is False
