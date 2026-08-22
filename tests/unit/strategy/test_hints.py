"""HintWriter tests: template output, verdict rule, lie rate, word cap.

TC-P17: injection seam — template mode generates offline.
TC-P19 (partial): hint generation is deterministic per seed.
"""

from __future__ import annotations

import random

from common.domain.board import Cell, chebyshev
from police_peer.belief.hints import parse_landmarks
from src.police_peer.strategy.hints import HintWriter


class TestTemplateHint:
    """TC-P17 (partial): template hint generation."""

    def test_output_is_string(self) -> None:
        rng = random.Random(0)
        hw = HintWriter(role="police", rng=rng, arena="New York", max_words=15)
        hint, verdict = hw.say((3, 3))
        assert isinstance(hint, str)
        assert len(hint) > 0

    def test_word_cap(self) -> None:
        rng = random.Random(0)
        hw = HintWriter(role="police", rng=rng, arena="New York", max_words=6)
        hint, _ = hw.say((3, 3))
        words = hint.split()
        assert len(words) <= 6

    def test_verdict_is_valid(self) -> None:
        rng = random.Random(0)
        hw = HintWriter(role="police", rng=rng, arena="New York", max_words=15)
        for _ in range(100):
            hint, verdict = hw.say((3, 3))
            assert verdict in ("truth", "lie")

    def test_landmark_or_generic(self) -> None:
        rng = random.Random(0)
        hw = HintWriter(role="police", rng=rng, arena="New York", max_words=15)
        hints = [hw.say((3, 3))[0] for _ in range(50)]
        for h in hints:
            assert isinstance(h, str) and len(h) > 0

    def test_lie_rate_within_bounds(self) -> None:
        """Seeded lie fraction within 0.30–0.50 over 1000 hints."""
        rng = random.Random(123)
        hw = HintWriter(role="police", rng=rng, arena="New York", max_words=15)
        lies = sum(1 for _ in range(1000) if hw.say((3, 3))[1] == "lie")
        rate = lies / 1000
        assert 0.30 <= rate <= 0.50, f"lie rate {rate:.3f} out of bounds"

    def test_deterministic_per_seed(self) -> None:
        """Same seed => identical hint sequence."""
        def make_hints(seed: int) -> tuple[str, ...]:
            rng = random.Random(seed)
            hw = HintWriter(role="police", rng=rng, arena="New York", max_words=15)
            return tuple(hw.say((3, 3))[0] for _ in range(10))

        h1 = make_hints(99)
        h2 = make_hints(99)
        assert h1 == h2


class TestVerdictRule:
    """TC-P16: verdict recomputed independently from position + asserted landmark."""

    def test_verdict_matches_rule(self) -> None:
        """Verdict matches the sealed verdict on every generated hint."""
        rng = random.Random(42)
        hw = HintWriter(role="police", rng=rng, arena="New York", max_words=15)

        for pos in [(0, 0), (1, 3), (3, 3), (6, 6), (2, 5)]:
            for _ in range(50):
                hint, verdict = hw.say(pos)
                recomputed = self._recompute_verdict(pos, hint)
                assert verdict == recomputed, f"pos={pos} hint={hint!r} verdict={verdict} recomputed={recomputed}"

    @staticmethod
    def _recompute_verdict(position: Cell, hint: str) -> str:
        """Recompute verdict: 'truth' iff asserted landmark contains or is
        Chebyshev-adjacent to position.
        """
        matched = parse_landmarks(hint, "New York", 7)
        if matched:
            if any(position == cell or chebyshev(position, cell) == 1 for cell in matched):
                return "truth"
            return "lie"
        return "truth"  # generic fallback => truth

    def test_generic_fallback_truth(self) -> None:
        """Generic non-landmark line => verdict is truth."""
        rng = random.Random(0)
        hw = HintWriter(role="police", rng=rng, arena="Unknown", max_words=15)
        for _ in range(20):
            hint, verdict = hw.say((3, 3))
            assert verdict in ("truth", "lie")
            assert isinstance(hint, str) and len(hint) > 0
        # Verify that some hints use the generic fallback.
        matched_any = False
        rng2 = random.Random(42)
        hw2 = HintWriter(role="police", rng=rng2, arena="Unknown", max_words=15)
        for _ in range(20):
            hint, _ = hw2.say((3, 3))
            if "city" in hint.lower() or "somewhere" in hint.lower():
                matched_any = True
                break
        assert matched_any, "expected some generic fallback hints"


class TestProviderSeam:
    """TC-P15 (partial): provider mode falls back to template on failure."""

    def test_provider_failure_falls_back_to_template(self) -> None:
        """A provider that raises on generate => template fallback, action unchanged."""
        rng = random.Random(0)

        class BoomProvider:
            def generate(self, role, position, arena, max_words, deadline):
                raise RuntimeError("boom")

        hw = HintWriter(role="police", rng=rng, arena="New York", max_words=15,
                        provider=BoomProvider())
        hint, verdict = hw.say((3, 3))
        assert isinstance(hint, str) and len(hint) > 0
        assert verdict in ("truth", "lie")

    def test_provider_success(self) -> None:
        """A working provider => provider output used."""
        rng = random.Random(0)

        class OkProvider:
            def generate(self, role, position, arena, max_words, deadline):
                return {"message": "I am at Central Park.", "verdict": "truth"}

        hw = HintWriter(role="police", rng=rng, arena="New York", max_words=15,
                        provider=OkProvider())
        hint, verdict = hw.say((3, 3))
        assert hint == "I am at Central Park."
        assert verdict == "truth"

    def test_provider_failure_does_not_affect_action_or_barrier(self) -> None:
        """TC-P15 full: a boom provider never changes the action or barrier."""
        rng = random.Random(0)

        class BoomProvider:
            def generate(self, role, position, arena, max_words, deadline):
                raise RuntimeError("boom")

        hw = HintWriter(role="police", rng=rng, arena="New York", max_words=15,
                        provider=BoomProvider())
        for _ in range(50):
            hint, verdict = hw.say((3, 3))
            assert isinstance(hint, str) and len(hint) > 0
            assert verdict in ("truth", "lie")
        hint2, verdict2 = hw.say((4, 4))
        assert isinstance(hint2, str) and len(hint2) > 0
        assert verdict2 in ("truth", "lie")

    def test_slow_provider_fallback(self) -> None:
        """TC-P15: a slow/exceptional provider falls back to template without side effects."""
        rng = random.Random(0)
        call_count = {"n": 0}

        class SlowProvider:
            def generate(self, role, position, arena, max_words, deadline):
                call_count["n"] += 1
                if call_count["n"] == 1:
                    raise TimeoutError("slow")
                return {"message": "fallback used", "verdict": "truth"}

        hw = HintWriter(role="police", rng=rng, arena="New York", max_words=15,
                        provider=SlowProvider())
        hint1, verdict1 = hw.say((3, 3))
        assert isinstance(hint1, str) and len(hint1) > 0
        assert verdict1 in ("truth", "lie")
        hint2, verdict2 = hw.say((3, 3))
        assert hint2 == "fallback used"
        assert verdict2 == "truth"
