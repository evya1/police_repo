"""OpenRouter transport contract tests; every HTTP boundary is in-memory."""

from __future__ import annotations

import json
import urllib.error

import pytest

from police_peer.infra.openrouter_client import (
    MAX_OUTPUT_TOKENS,
    OpenRouterAuthenticationError,
    OpenRouterClient,
    OpenRouterConnectionError,
    OpenRouterMalformedResponseError,
    OpenRouterRateLimitError,
    OpenRouterTimeoutError,
)

_CREDENTIAL = "unit-credential"


class _Response:
    def __init__(self, body: dict | bytes) -> None:
        self.body = body if isinstance(body, bytes) else json.dumps(body).encode()

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, _limit: int) -> bytes:
        return self.body


def _body(*, usage: object = ...) -> dict:
    body = {
        "choices": [{"message": {"content": "Near Central Park."}}],
        "model": "actual/model",
        "provider": "Actual Provider",
    }
    if usage is ...:
        body["usage"] = {"prompt_tokens": 11, "completion_tokens": 4}
    elif usage is not None:
        body["usage"] = usage
    return body


def _client(opener, *, clock=lambda: 100.0, max_tokens: int = 8) -> OpenRouterClient:
    return OpenRouterClient(
        api_key=_CREDENTIAL,
        model="requested/model",
        provider_slug="novita",
        max_output_tokens=max_tokens,
        clock=clock,
        opener=opener,
    )


def test_success_extracts_actual_routing_and_usage_and_pins_request() -> None:
    seen = {}

    def open_(request, *, timeout):
        seen.update(request=request, timeout=timeout)
        return _Response(_body())

    result = _client(open_).complete("safe prompt", deadline=105.0)
    assert (result.text, result.model, result.provider) == (
        "Near Central Park.", "actual/model", "Actual Provider",
    )
    assert (result.input_tokens, result.output_tokens) == (11, 4)
    payload = json.loads(seen["request"].data)
    assert payload["max_tokens"] == 8
    assert payload["reasoning"] == {"enabled": False}
    assert payload["provider"] == {
        "only": ["novita"], "allow_fallbacks": False,
        "require_parameters": True, "data_collection": "deny",
    }
    assert seen["timeout"] == 5.0
    assert _CREDENTIAL not in seen["request"].data.decode()


def test_missing_usage_stays_unknown() -> None:
    result = _client(lambda *_args, **_kwargs: _Response(_body(usage=None))).complete(
        "prompt", deadline=None,
    )
    assert (result.input_tokens, result.output_tokens) == (None, None)


def _raising(exc: Exception):
    def open_(*_args, **_kwargs):
        raise exc

    return open_


@pytest.mark.parametrize("status", [401, 403])
def test_authentication_failures_are_classified_and_sanitized(status: int) -> None:
    error = urllib.error.HTTPError("https://service.invalid", status, "", {}, None)
    with pytest.raises(OpenRouterAuthenticationError) as caught:
        _client(_raising(error)).complete("private prompt", deadline=None)
    assert _CREDENTIAL not in str(caught.value)
    assert "private prompt" not in str(caught.value)


def test_rate_limit_is_classified_for_gatekeeper_retry() -> None:
    error = urllib.error.HTTPError("https://service.invalid", 429, "", {}, None)
    with pytest.raises(OpenRouterRateLimitError) as caught:
        _client(_raising(error)).complete("prompt", deadline=None)
    assert caught.value.status_code == 429


@pytest.mark.parametrize("exc", [TimeoutError(), urllib.error.URLError(TimeoutError())])
def test_timeout_failures_are_classified(exc: Exception) -> None:
    with pytest.raises(OpenRouterTimeoutError):
        _client(_raising(exc)).complete("prompt", deadline=None)


def test_connection_failure_is_classified() -> None:
    with pytest.raises(OpenRouterConnectionError):
        _client(_raising(urllib.error.URLError("offline"))).complete("prompt", deadline=None)


@pytest.mark.parametrize("body", [b"not-json", b"{}", b'{"choices":[]}'])
def test_malformed_responses_are_classified(body: bytes) -> None:
    with pytest.raises(OpenRouterMalformedResponseError):
        _client(lambda *_args, **_kwargs: _Response(body)).complete("prompt", deadline=None)


def test_expired_deadline_never_opens_a_connection() -> None:
    called = False

    def open_(*_args, **_kwargs):
        nonlocal called
        called = True

    with pytest.raises(OpenRouterTimeoutError):
        _client(open_).complete("prompt", deadline=100.0)
    assert called is False


def test_output_token_cap_is_enforced_at_construction() -> None:
    with pytest.raises(ValueError, match="max_output_tokens"):
        _client(lambda *_args, **_kwargs: None, max_tokens=MAX_OUTPUT_TOKENS + 1)
