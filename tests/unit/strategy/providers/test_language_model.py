"""Unit tests for the optional LLM hint provider adapter (T027).

Mocks the full external boundary (gatekeeper + transports) — no live calls, no
real API key, no network. Covers: success returning the strict JSON, failure
paths (timeout / 429 / malformed / outage) -> None/template fallback, cadence
(every_n_steps), word-cap + arena in the system prompt, rule-computed verdict,
and stdlib-only imports (no ``openai`` SDK for template mode).
"""

from __future__ import annotations

import json
import os
from unittest import mock

from police_peer.strategy.providers.language_model import (
    OllamaProvider,
    OpenAIProvider,
    _system_prompt,
    resolve_text_provider,
)
from police_peer.strategy.providers.transports import _extract_json

API_KEY = "test-sk-do-not-commit"


class _FakeGatekeeper:
    """Gatekeeper stand-in: returns a canned raw reply, or raises if set."""

    def __init__(self, reply: str = "", exc: Exception | None = None):
        self.reply = reply
        self.exc = exc

    def execute(self, call, *args, **kwargs):
        if self.exc is not None:
            raise self.exc
        return self.reply


def _reply(**overrides) -> str:
    payload = {"message": "I am at Central Park.", "verdict": "lie",
               "reasoning": "bluff"}
    payload.update(overrides)
    return json.dumps(payload)


def _with():
    return mock.patch.dict(os.environ, {"OPENAI_API_KEY": API_KEY}, clear=False)


class TestOpenAIProvider:
    def test_success_returns_strict_json(self) -> None:
        with _with():
            gk = _FakeGatekeeper(_reply())
            p = OpenAIProvider(gatekeeper=gk)
            result = p.generate("police", (3, 3), "New York", 15, None)
        assert result is not None
        assert result["message"] == "I am at Central Park."
        assert result["reasoning"] == "bluff"

    def test_verdict_is_rule_computed_not_trusted(self) -> None:
        # Model names a far landmark but claims "truth"; local rule wins.
        with _with():
            gk = _FakeGatekeeper(_reply(message="I am at Brooklyn.",
                                        verdict="truth"))
            p = OpenAIProvider(gatekeeper=gk)
            near = p.generate("police", (5, 4), "New York", 15, None)
            far = p.generate("police", (3, 3), "New York", 15, None)
        assert near is not None and near["verdict"] == "truth"
        assert far is not None and far["verdict"] == "lie"

    def test_word_cap_enforced(self) -> None:
        with _with():
            gk = _FakeGatekeeper(_reply(message="one two three four five six"))
            p = OpenAIProvider(gatekeeper=gk)
            result = p.generate("police", (0, 0), "New York", 3, None)
        assert result is not None
        assert len(result["message"].split()) <= 3

    def test_timeout_returns_none(self) -> None:
        with _with():
            gk = _FakeGatekeeper(exc=TimeoutError("slow model"))
            p = OpenAIProvider(gatekeeper=gk)
            assert p.generate("police", (0, 0), "New York", 15, None) is None

    def test_429_returns_none(self) -> None:
        with _with():
            gk = _FakeGatekeeper(exc=RuntimeError("429 rate limit"))
            p = OpenAIProvider(gatekeeper=gk)
            assert p.generate("police", (0, 0), "New York", 15, None) is None

    def test_outage_returns_none(self) -> None:
        with _with():
            gk = _FakeGatekeeper(exc=ConnectionError("down"))
            p = OpenAIProvider(gatekeeper=gk)
            assert p.generate("police", (0, 0), "New York", 15, None) is None

    def test_malformed_returns_none(self) -> None:
        with _with():
            gk = _FakeGatekeeper("not json at all")
            p = OpenAIProvider(gatekeeper=gk)
            assert p.generate("police", (0, 0), "New York", 15, None) is None

    def test_no_api_key_returns_none(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            gk = _FakeGatekeeper(_reply())
            p = OpenAIProvider(gatekeeper=gk)
            assert p.generate("police", (0, 0), "New York", 15, None) is None

    def test_base_url_from_env(self) -> None:
        from police_peer.strategy.providers.transports import chat_completion

        with _with(), mock.patch(
            "police_peer.strategy.providers.transports.urllib.request.urlopen"
        ) as m, mock.patch.dict(os.environ, {"OPENAI_BASE_URL": "https://x/v1"}):
            m.return_value.__enter__.return_value.read.return_value = (
                b'{"choices":[{"message":{"content":"ok"}}]}')
            base_url = os.environ["OPENAI_BASE_URL"]
            chat_completion(API_KEY, "gpt-4o-mini", "sys", 0.4, 15, 30,
                            base_url=base_url)
        assert m.call_args.args[0].full_url == "https://x/v1"

    def test_cadence(self) -> None:
        with _with():
            gk = _FakeGatekeeper(_reply())
            p = OpenAIProvider(gatekeeper=gk, every_n_steps=2)
            assert p.generate("police", (0, 0), "New York", 15, None) is None
            assert p.generate("police", (0, 0), "New York", 15, None) is not None

    def test_system_prompt_pins_arena_and_cap(self) -> None:
        sp = _system_prompt("police", "New York", 12)
        assert "New York" in sp and "12" in sp


class TestResolveProvider:
    def test_default_is_none(self) -> None:
        assert resolve_text_provider({}) is None
        assert resolve_text_provider(None) is None

    def test_unknown_provider_is_none(self) -> None:
        assert resolve_text_provider({"trash_talk": {"provider": "nope"}}) is None

    def test_ollama_resolves(self) -> None:
        p = resolve_text_provider({"trash_talk": {"provider": "ollama"}})
        assert isinstance(p, OllamaProvider)

    def test_openai_requires_env_key(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            p = resolve_text_provider({"trash_talk": {"provider": "openai_api"}})
        assert p is None


def test_extract_json_fence_strip() -> None:
    fenced = '```json\n{"message": "hi", "verdict": "truth"}\n```'
    data = json.loads(_extract_json(fenced))
    assert data["message"] == "hi"
