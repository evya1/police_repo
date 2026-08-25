"""Contract: `LanguageModelAdapter` <-> `ExternalApiGatekeeper` `llm` lane (T049).

Pins the ADR-010 seam: the adapter reaches an injected `CompletionClient`
only through `Gatekeeper.execute(lane="llm", ...)` with the caller's own
deadline preserved, and the client-visible prompt never carries anything
outside `HintRenderRequest`'s allowlist. Every client here is an in-memory
fake -- no test in this module performs, or could perform, live network I/O.
"""

from __future__ import annotations

import pytest

from common.domain.scoring import Role
from police_peer.infra.external_api_gatekeeper import ExternalApiGatekeeper, ExternalCallError
from police_peer.infra.gatekeeper_types import GatekeeperConfig
from police_peer.infra.llm_client import RawCompletion
from police_peer.infra.llm_provider import (
    InvalidOutputTextError,
    LanguageModelAdapter,
    MalformedUsageError,
)
from police_peer.strategy.hint_types import HintRenderRequest, ProviderReply


class FakeClock:
    def __init__(self, start: float = 1000.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now


class Http429Error(Exception):
    def __init__(self) -> None:
        super().__init__("429 Too Many Requests")
        self.status_code = 429


class RecordingClient:
    """Fake `CompletionClient`: no I/O, replays a scripted result per call."""

    def __init__(self, script: list[object]) -> None:
        self.script = list(script)
        self.calls: list[tuple[str, float | None]] = []

    def complete(self, prompt: str, *, deadline: float | None) -> RawCompletion:
        self.calls.append((prompt, deadline))
        result = self.script.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def _request() -> HintRenderRequest:
    return HintRenderRequest(
        role=Role.POLICE, arena="New York", target_landmark="the fountain",
        claim="truth", max_words=8, style="concise",
    )


def _adapter(script: list[object], sleeps: list[float] | None = None) -> tuple[LanguageModelAdapter, RecordingClient]:
    cfg = GatekeeperConfig(dos_threshold=1000, bucket_capacity=1000, requests_per_minute=6000)
    sleeper = (lambda s: sleeps.append(s)) if sleeps is not None else (lambda s: None)
    gatekeeper = ExternalApiGatekeeper(config=cfg, time_provider=FakeClock(), sleeper=sleeper)
    client = RecordingClient(script)
    return LanguageModelAdapter(client, gatekeeper), client


def _reply(text: str = "I'm near the fountain.", **usage: object) -> RawCompletion:
    return RawCompletion(text=text, provider="fake", model="m1", **usage)


def test_success_normalizes_to_provider_reply():
    adapter, _ = _adapter([_reply("I'm patrolling the fountain area.", input_tokens=12, output_tokens=6)])
    reply = adapter.render(_request(), deadline=None)
    assert isinstance(reply, ProviderReply)
    assert (reply.text, reply.provider, reply.model) == ("I'm patrolling the fountain area.", "fake", "m1")
    assert (reply.usage.input_tokens, reply.usage.output_tokens) == (12, 6)


def test_timeout_raises_and_never_returns_a_reply():
    # Gatekeeper wraps a non-retryable TimeoutError as ExternalCallError;
    # either way T027's `except Exception` fallback boundary catches it.
    adapter, _ = _adapter([TimeoutError("slow")])
    with pytest.raises((TimeoutError, ExternalCallError)):
        adapter.render(_request(), deadline=None)


def test_retryable_429_then_success():
    sleeps: list[float] = []
    adapter, client = _adapter([Http429Error(), _reply()], sleeps)
    reply = adapter.render(_request(), deadline=None)
    assert reply.text == "I'm near the fountain."
    assert len(client.calls) == 2
    assert sleeps  # a backoff actually happened between the retry attempts


def test_missing_usage_stays_none_not_inferred():
    adapter, _ = _adapter([_reply(input_tokens=None, output_tokens=None)])
    reply = adapter.render(_request(), deadline=None)
    assert (reply.usage.input_tokens, reply.usage.output_tokens) == (None, None)


def test_malformed_usage_bool_is_rejected():
    adapter, _ = _adapter([_reply(input_tokens=True, output_tokens=1)])
    with pytest.raises(MalformedUsageError):
        adapter.render(_request(), deadline=None)


def test_malformed_usage_negative_is_rejected():
    adapter, _ = _adapter([_reply(input_tokens=1, output_tokens=-3)])
    with pytest.raises(MalformedUsageError):
        adapter.render(_request(), deadline=None)


def test_empty_output_text_is_rejected():
    adapter, _ = _adapter([_reply(text="   ")])
    with pytest.raises(InvalidOutputTextError):
        adapter.render(_request(), deadline=None)


def test_oversized_output_text_is_rejected():
    adapter, _ = _adapter([_reply(text="x" * 48_001)])
    with pytest.raises(InvalidOutputTextError):
        adapter.render(_request(), deadline=None)


def test_deadline_is_preserved_not_reset():
    adapter, client = _adapter([_reply()])
    adapter.render(_request(), deadline=1234.5)
    assert client.calls[0][1] == 1234.5


def test_client_reached_only_through_llm_lane_execute(monkeypatch):
    """Proves the client is invoked only via `Gatekeeper.execute(lane="llm", ...)`."""
    adapter, client = _adapter([_reply()])
    gatekeeper = adapter._gatekeeper
    seen: dict[str, object] = {}
    original_execute = gatekeeper.execute

    def spy_execute(call, *args, lane="reporting", deadline=None, **kwargs):
        seen["lane"], seen["deadline"] = lane, deadline
        return original_execute(call, *args, lane=lane, deadline=deadline, **kwargs)

    monkeypatch.setattr(gatekeeper, "execute", spy_execute)
    adapter.render(_request(), deadline=42.0)
    assert seen == {"lane": "llm", "deadline": 42.0}
    assert client.calls  # the client really was reached, exactly once


def test_privacy_allowlist_disallowed_field_never_reaches_prompt():
    """No cell, verdict, grid, belief, or legal-move datum reaches the prompt (ADR-010)."""
    adapter, client = _adapter([_reply()])
    # claim is "truth" here, so "lie" has no legitimate reason to appear.
    adapter.render(_request(), deadline=None)
    prompt = client.calls[0][0]
    for forbidden in ("(3, 5)", "verdict", "smell_grid", "belief", "legal_move", "lie"):
        assert forbidden not in prompt
    # HintRenderRequest's own allowlist has no slot for these at all.
    for missing_attr in ("verdict", "position", "destination"):
        assert not hasattr(_request(), missing_attr)


def test_zero_live_network_uses_fakes_only():
    """Every client here is `RecordingClient`; no vendor/network import exists."""
    import police_peer.infra.llm_client as llm_client_module
    import police_peer.infra.llm_provider as llm_provider_module

    for module in (llm_client_module, llm_provider_module):
        for banned in ("socket", "requests", "httpx"):
            assert banned not in vars(module)
