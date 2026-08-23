"""Unit tests: prompt building and raw-response normalization (T049).

Pure-function coverage for `police_peer.infra.llm_provider`, separate from the
contract-level Gatekeeper-lane and privacy-allowlist tests in
`tests/contract/test_llm_provider_contract.py`.
"""

from __future__ import annotations

import pytest

from common.domain.scoring import Role
from police_peer.infra.llm_client import RawCompletion
from police_peer.infra.llm_provider import (
    PROMPT_VERSION,
    InvalidOutputTextError,
    MalformedUsageError,
    _normalize_text,
    _normalize_usage,
    build_prompt,
)
from police_peer.strategy.hint_types import HintRenderRequest


def _request(**overrides: object) -> HintRenderRequest:
    fields: dict[str, object] = {
        "role": Role.POLICE, "arena": "New York", "target_landmark": "the fountain",
        "claim": "truth", "max_words": 8, "style": "concise",
    }
    fields.update(overrides)
    return HintRenderRequest(**fields)  # type: ignore[arg-type]


def test_prompt_is_versioned():
    assert build_prompt(_request()).startswith(PROMPT_VERSION)


def test_prompt_is_deterministic_for_identical_request():
    assert build_prompt(_request()) == build_prompt(_request())


def test_prompt_changes_with_claim():
    truth = build_prompt(_request(claim="truth"))
    lie = build_prompt(_request(claim="lie"))
    assert truth != lie


def test_prompt_requests_plain_text_not_json():
    prompt = build_prompt(_request())
    assert "JSON" in prompt
    assert "{" not in prompt and "}" not in prompt


def test_prompt_contains_only_allowlisted_fields():
    req = _request(arena="Zurich", target_landmark="the clock tower")
    prompt = build_prompt(req)
    assert "Zurich" in prompt
    assert "the clock tower" in prompt
    assert "police" in prompt
    assert "truth" in prompt
    assert "concise" in prompt
    assert "8" in prompt


def _raw(**overrides: object) -> RawCompletion:
    fields: dict[str, object] = {
        "text": "I'm patrolling the fountain area.", "provider": "fake-provider",
        "model": "fake-model-1", "input_tokens": 10, "output_tokens": 5,
    }
    fields.update(overrides)
    return RawCompletion(**fields)  # type: ignore[arg-type]


def test_normalize_usage_known_counts():
    usage = _normalize_usage(_raw(input_tokens=10, output_tokens=5))
    assert (usage.input_tokens, usage.output_tokens) == (10, 5)


def test_normalize_usage_none_stays_none():
    usage = _normalize_usage(_raw(input_tokens=None, output_tokens=None))
    assert usage.input_tokens is None
    assert usage.output_tokens is None


def test_normalize_usage_rejects_bool():
    with pytest.raises(MalformedUsageError):
        _normalize_usage(_raw(input_tokens=True))


def test_normalize_usage_rejects_negative():
    with pytest.raises(MalformedUsageError):
        _normalize_usage(_raw(output_tokens=-1))


def test_normalize_usage_rejects_non_int_type():
    with pytest.raises(MalformedUsageError):
        _normalize_usage(_raw(input_tokens="10"))


def test_normalize_text_accepts_valid_string():
    assert _normalize_text("hello there") == "hello there"


def test_normalize_text_rejects_empty():
    with pytest.raises(InvalidOutputTextError):
        _normalize_text("   ")


def test_normalize_text_rejects_non_string():
    with pytest.raises(InvalidOutputTextError):
        _normalize_text(12345)


def test_normalize_text_rejects_oversized():
    with pytest.raises(InvalidOutputTextError):
        _normalize_text("x" * 2001)
