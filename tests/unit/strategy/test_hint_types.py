"""hint_types.py contract tests (T027).

Structural proof that the provider seam cannot carry authority: ProviderReply
has no verdict/action/barrier/target/score/legality field (closes F-12), and
every type is frozen (immutable audit evidence).
"""

from __future__ import annotations

import dataclasses

import pytest

from common.domain.scoring import Role
from police_peer.strategy.hint_types import (
    NON_CLAIM,
    FallbackReason,
    HintPlan,
    HintRenderRequest,
    HintResult,
    ProviderReply,
    TokenUsage,
)

_FORBIDDEN_REPLY_FIELDS = {"verdict", "action", "barrier", "target", "score", "legality"}
_ALLOWED_REQUEST_FIELDS = {"role", "arena", "target_landmark", "claim", "max_words", "style"}


class TestProviderReplyHasNoAuthority:
    def test_no_forbidden_fields(self) -> None:
        names = {f.name for f in dataclasses.fields(ProviderReply)}
        assert names.isdisjoint(_FORBIDDEN_REPLY_FIELDS)

    def test_fields_are_wording_and_metadata_only(self) -> None:
        names = {f.name for f in dataclasses.fields(ProviderReply)}
        assert names == {"text", "usage", "provider", "model"}


class TestHintRenderRequestAllowlist:
    def test_fields_are_exactly_the_allowlist(self) -> None:
        names = {f.name for f in dataclasses.fields(HintRenderRequest)}
        assert names == _ALLOWED_REQUEST_FIELDS

    def test_default_style_is_concise(self) -> None:
        req = HintRenderRequest(
            role=Role.POLICE, arena="New York", target_landmark="Brooklyn",
            claim="truth", max_words=15,
        )
        assert req.style == "concise"

    def test_frozen(self) -> None:
        req = HintRenderRequest(
            role=Role.POLICE, arena="New York", target_landmark="Brooklyn",
            claim="truth", max_words=15,
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            req.claim = "lie"  # type: ignore[misc]


class TestTokenUsage:
    def test_unknown_is_none_not_inferred(self) -> None:
        usage = TokenUsage(input_tokens=None, output_tokens=None)
        assert usage.input_tokens is None
        assert usage.output_tokens is None

    def test_frozen(self) -> None:
        usage = TokenUsage(1, 2)
        with pytest.raises(dataclasses.FrozenInstanceError):
            usage.input_tokens = 3  # type: ignore[misc]


class TestHintPlan:
    def test_non_claim_has_no_landmark(self) -> None:
        plan = HintPlan(claim=NON_CLAIM, target_landmark=None, fallback_text="I'm somewhere.")
        assert plan.target_landmark is None
        assert plan.claim == NON_CLAIM

    def test_frozen(self) -> None:
        plan = HintPlan(claim="truth", target_landmark="Brooklyn", fallback_text="x")
        with pytest.raises(dataclasses.FrozenInstanceError):
            plan.claim = "lie"  # type: ignore[misc]


class TestHintResultAndFallbackReason:
    def test_fields(self) -> None:
        result = HintResult(
            text="hi", verdict="truth", fallback_reason=FallbackReason.TIMEOUT,
            usage=TokenUsage(0, 0),
        )
        assert result.text == "hi"
        assert result.fallback_reason is FallbackReason.TIMEOUT

    def test_all_reasons_distinct(self) -> None:
        values = {reason.value for reason in FallbackReason}
        assert len(values) == len(list(FallbackReason))

    def test_frozen(self) -> None:
        result = HintResult("hi", "truth", None, TokenUsage(0, 0))
        with pytest.raises(dataclasses.FrozenInstanceError):
            result.text = "bye"  # type: ignore[misc]
