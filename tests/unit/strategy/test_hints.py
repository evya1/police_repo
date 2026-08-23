"""HintWriter tests: local plan, provider seam, validation, usage sealing (T027)."""

from __future__ import annotations

import random

import pytest

from common.domain.board import Cell, chebyshev
from police_peer.belief.hints import parse_landmarks
from police_peer.strategy.hint_types import FallbackReason, ProviderReply, TokenUsage
from police_peer.strategy.hints import HintWriter


class _FixedRng:
    """Deterministic stand-in for random.Random: fixed roll + first choice."""

    def __init__(self, roll: float) -> None:
        self._roll = roll

    def random(self) -> float:
        return self._roll

    def choice(self, seq):
        return seq[0]


class _Provider:
    def __init__(self, text="I am at Central Park.", usage=None):
        self.text = text
        self.usage = usage if usage is not None else TokenUsage(3, 5)
        self.calls: list = []

    def render(self, request, *, deadline=None):
        self.calls.append(request)
        return ProviderReply(text=self.text, usage=self.usage, provider="p", model="m")


class _RaisingProvider:
    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    def render(self, request, *, deadline=None):
        raise self._exc


class _MalformedProvider:
    def render(self, request, *, deadline=None):
        return {"message": "not a ProviderReply"}


class TestTemplateHint:
    def test_word_cap_uses_configured_value_not_hardcoded_15(self) -> None:
        """F-13: a value below 15 must be enforced, proving 15 is never hard-coded."""
        hw = HintWriter(role="police", rng=random.Random(0), arena="New York", max_words=3)
        for _ in range(50):
            hint, _ = hw.say((3, 3))
            assert len(hint.split()) <= 3

    def test_lie_rate_within_bounds(self) -> None:
        hw = HintWriter(role="police", rng=random.Random(123), arena="New York", max_words=15)
        lies = sum(1 for _ in range(1000) if hw.say((3, 3))[1] == "lie")
        assert 0.30 <= lies / 1000 <= 0.50

    def test_deterministic_per_seed(self) -> None:
        def run(seed: int) -> tuple[str, ...]:
            hw = HintWriter(role="police", rng=random.Random(seed), arena="New York", max_words=15)
            return tuple(hw.say((3, 3))[0] for _ in range(10))

        assert run(99) == run(99)

    def test_verdict_matches_recomputed_rule(self) -> None:
        hw = HintWriter(role="police", rng=random.Random(42), arena="New York", max_words=15)
        for pos in [(0, 0), (1, 3), (3, 3), (6, 6), (2, 5)]:
            for _ in range(30):
                hint, verdict = hw.say(pos)
                assert verdict == _recompute_verdict(pos, hint)


def _recompute_verdict(position: Cell, hint: str) -> str:
    matched = parse_landmarks(hint, "New York", 7)
    if matched:
        if any(position == c or chebyshev(position, c) == 1 for c in matched):
            return "truth"
        return "lie"
    return "truth"


class TestNonClaim:
    """(6, 0) is truth-incompatible with every named + generic New York region:
    no claim can be truthfully made, so no landmark is fabricated (ADR-010).
    """

    def test_no_truth_compatible_region_never_calls_provider(self) -> None:
        provider = _Provider()
        hw = HintWriter(
            role="police", rng=_FixedRng(roll=0.9), arena="New York", max_words=15,
            provider=provider,
        )
        hint, verdict = hw.say((6, 0))
        assert verdict == "truth"
        assert provider.calls == []
        assert hw.last_result is not None
        assert hw.last_result.fallback_reason == FallbackReason.NON_CLAIM
        assert "the city" in hint.lower()


class TestProviderSeam:
    def test_no_provider_uses_template_and_records_reason(self) -> None:
        hw = HintWriter(role="police", rng=random.Random(0), arena="New York", max_words=15)
        hw.say((3, 3))
        assert hw.last_result.fallback_reason == FallbackReason.NO_PROVIDER
        assert hw.last_result.usage == TokenUsage(0, 0)

    def test_provider_success_uses_provider_text_and_plan_verdict(self) -> None:
        provider = _Provider(text="I'm patrolling the Central Park area.")
        hw = HintWriter(role="police", rng=_FixedRng(roll=0.9), arena="New York", max_words=15,
                         provider=provider)
        hint, verdict = hw.say((1, 3))
        assert hint == "I'm patrolling the Central Park area."
        assert verdict == "truth"
        assert hw.last_result.fallback_reason is None
        assert hw.last_result.usage == TokenUsage(3, 5)
        assert provider.calls[0].target_landmark == "Central Park"
        assert provider.calls[0].claim == "truth"

    @pytest.mark.parametrize(
        ("provider", "reason"),
        [
            (_RaisingProvider(TimeoutError("slow")), FallbackReason.TIMEOUT),
            (_RaisingProvider(RuntimeError("boom")), FallbackReason.EXCEPTION),
            (_MalformedProvider(), FallbackReason.MALFORMED),
        ],
        ids=["timeout", "exception", "malformed"],
    )
    def test_every_failure_is_typed_never_a_bare_pass(self, provider, reason) -> None:
        hw = HintWriter(role="police", rng=random.Random(0), arena="New York", max_words=15,
                         provider=provider)
        hint, verdict = hw.say((3, 3))
        assert isinstance(hint, str) and len(hint) > 0
        assert verdict in ("truth", "lie")
        assert hw.last_result.fallback_reason == reason
        # A call was attempted (raised or malformed reply); usage is UNKNOWN,
        # never assumed zero -- a fallback must not erase billed tokens.
        assert hw.last_result.usage == TokenUsage(None, None)


class TestTextValidation:
    """(1, 3) + _FixedRng(0.9) deterministically plans "Central Park" (truth)."""

    def _result(self, text: str, usage=None, max_words: int = 15):
        hw = HintWriter(role="police", rng=_FixedRng(roll=0.9), arena="New York",
                         max_words=max_words, provider=_Provider(text=text, usage=usage))
        hw.say((1, 3))
        return hw.last_result

    def _reason(self, text: str, max_words: int = 15) -> FallbackReason | None:
        return self._result(text, max_words=max_words).fallback_reason

    def test_valid_text_uses_provider(self) -> None:
        assert self._reason("I'm near Central Park.") is None

    def test_nfc_normalization_does_not_itself_reject(self) -> None:
        assert self._reason("I'm near Central Park café.") is None

    @pytest.mark.parametrize(
        ("text", "max_words"),
        [
            ("   ", 15),
            ("I'm near Central Park.\nSecond line.", 15),
            ("I am near the Central Park area today for sure", 3),
            ("I'm near Brooklyn.", 15),
            ("I'm near Central Park, not Brooklyn.", 15),
            ("Central Park, cell (1, 3).", 15),
            ("Central Park\x07 area.", 15),
            ("```Central Park```", 15),
        ],
        ids=["empty", "multiline", "over_cap", "missing_landmark", "extra_landmark",
             "coordinate", "control_char", "code_fence"],
    )
    def test_invalid_text_rejected(self, text: str, max_words: int) -> None:
        assert self._reason(text, max_words) == FallbackReason.INVALID_TEXT

    def test_rejected_text_preserves_reported_usage(self) -> None:
        """A billed call's usage survives a fallback (ADR-010/LLM-09)."""
        result = self._result("I'm near Brooklyn.", usage=TokenUsage(7, 3))
        assert result.fallback_reason == FallbackReason.INVALID_TEXT
        assert result.usage == TokenUsage(7, 3)

    def test_rejected_text_with_no_reported_usage_seals_unknown(self) -> None:
        result = self._result("I'm near Brooklyn.", usage=TokenUsage(None, None))
        assert result.fallback_reason == FallbackReason.INVALID_TEXT
        assert result.usage == TokenUsage(None, None)
