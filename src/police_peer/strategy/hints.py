"""HintWriter -- local deterministic hint plan + optional TextProvider wording.

Local code selects the claim (truth/lie/non-claim), the destination-based
landmark, and the verdict (STRAT-008); a TextProvider, if present, supplies
wording only, through the allowlisted ``HintRenderRequest`` (ADR-010). Every
typed or unexpected provider failure falls back to the plan's own
deterministic template with a recorded ``FallbackReason``; the verdict is
never taken from the provider (closes F-12/F-13).
"""

from __future__ import annotations

import random
import re
import unicodedata

from common.domain.board import Cell, chebyshev
from common.domain.scoring import Role
from police_peer.belief.hints import GENERIC_FALLBACK, LANDMARK_CELLS

from .hint_types import (
    NON_CLAIM,
    FallbackReason,
    HintPlan,
    HintRenderRequest,
    HintResult,
    ProviderReply,
    TextProvider,
    TokenUsage,
)

__all__ = ["HintWriter", "TextProvider"]

_COORD_RE = re.compile(
    r"[\(\[]\s*-?\d+\s*,\s*-?\d+\s*[\)\]]|\brow\s*\d+\b|\bcol(?:umn)?\s*\d+\b", re.IGNORECASE,
)
_FENCE_CHARS = "`{}"
_LIE_TEMPLATES = [
    "I'm somewhere near {landmark}.", "Look for me in the {landmark} zone.",
    "I've been around {landmark} today.", "My location is close to {landmark}.",
]
_TRUTH_TEMPLATES: dict[Role, list[str]] = {
    Role.POLICE: [
        "I'm patrolling the {landmark} area.", "You'll find me near {landmark}.",
        "I'm guarding the {landmark} district.", "The {landmark} sector is my post.",
    ],
    Role.THIEF: [
        "I'm in the {landmark} area.", "You'll find me near {landmark}.",
        "I'm hiding around {landmark}.", "The {landmark} district is where I am.",
    ],
}


class HintWriter:
    """Template-default verbal layer (STRAT-008); provider supplies wording only."""

    def __init__(
        self,
        role: Role,
        rng: random.Random,
        arena: str,
        max_words: int,
        provider: TextProvider | None = None,
    ) -> None:
        self.role = role
        self.rng = rng
        self.arena = arena
        self.max_words = max_words
        self.provider = provider
        # Sealed audit state (SEC-009), never part of the public (hint,
        # verdict) return. Per-turn: valid only until the next say() call --
        # callers (e.g. BrainBase.decide) must read it immediately after.
        self.last_result: HintResult | None = None

    def say(self, position: Cell, *, deadline: float | None = None) -> tuple[str, str]:
        """(hint, verdict). Plan first (pure), then render (provider optional)."""
        result = self._render(self._plan(position), deadline=deadline)
        self.last_result = result
        return result.text, result.verdict

    def _plan(self, position: Cell) -> HintPlan:
        """Pick claim + destination landmark; never fabricate one (ADR-010)."""
        want_lie = self.rng.random() < 0.4
        landmark = self._pick_landmark(position, want_lie)
        if landmark is None:
            return HintPlan(NON_CLAIM, None, "I'm somewhere in the city.")
        claim = self._verdict(position, landmark)
        templates = _LIE_TEMPLATES if claim == "lie" else _TRUTH_TEMPLATES[self.role]
        text = self._cap(self.rng.choice(templates).format(landmark=landmark))
        return HintPlan(claim, landmark, text)

    def _render(self, plan: HintPlan, *, deadline: float | None) -> HintResult:
        if plan.claim == NON_CLAIM or plan.target_landmark is None:
            return HintResult(plan.fallback_text, "truth", FallbackReason.NON_CLAIM, TokenUsage(0, 0))
        if self.provider is None:
            return self._fallback(plan, FallbackReason.NO_PROVIDER, TokenUsage(0, 0))
        request = HintRenderRequest(
            role=self.role, arena=self.arena, target_landmark=plan.target_landmark,
            claim=plan.claim, max_words=self.max_words,
        )
        try:
            reply = self.provider.render(request, deadline=deadline)
            if not isinstance(reply, ProviderReply):
                # A call happened; its usage is unavailable, never assumed zero.
                return self._fallback(plan, FallbackReason.MALFORMED, TokenUsage(None, None))
            text = unicodedata.normalize("NFC", reply.text)
        except TimeoutError:
            # A call may have been billed; unknown, never assumed zero (ADR-010/LLM-09).
            return self._fallback(plan, FallbackReason.TIMEOUT, TokenUsage(None, None))
        except Exception:  # noqa: BLE001 -- typed fallback boundary (ADR-010)
            return self._fallback(plan, FallbackReason.EXCEPTION, TokenUsage(None, None))
        if not self._valid_text(text, plan.target_landmark):
            # The call succeeded and was billed; its reported usage stands.
            return self._fallback(plan, FallbackReason.INVALID_TEXT, reply.usage)
        return HintResult(text, plan.claim, None, reply.usage)

    def _fallback(self, plan: HintPlan, reason: FallbackReason, usage: TokenUsage) -> HintResult:
        return HintResult(plan.fallback_text, plan.claim, reason, usage)

    def _valid_text(self, text: str, landmark: str) -> bool:
        """NFC-normalized already. Strict allowlist validation (ADR-010)."""
        if not text.strip() or "\n" in text or "\r" in text:
            return False
        if len(text.split()) > self.max_words:
            return False
        lowered = text.lower()
        if landmark.lower() not in lowered:
            return False
        others = [*LANDMARK_CELLS.get(self.arena, {}), *GENERIC_FALLBACK]
        if any(o.lower() in lowered for o in others if o != landmark):
            return False
        if _COORD_RE.search(text) or any(ord(ch) < 32 for ch in text):
            return False
        return not any(ch in _FENCE_CHARS for ch in text)

    def _pick_landmark(self, position: Cell, want_lie: bool) -> str | None:
        """Truth-compatible (or, for a lie, incompatible) landmark for
        `position` -- named or generic, only when actually (in)compatible.
        """
        regions = self._all_regions()
        candidates = [
            name for name, cells in regions.items()
            if self._region_contains_or_adjacent(position, cells) != want_lie
        ]
        return self.rng.choice(candidates) if candidates else None

    def _all_regions(self) -> dict[str, list[Cell]]:
        regions: dict[str, list[Cell]] = dict(LANDMARK_CELLS.get(self.arena, {}))
        for name, cells in GENERIC_FALLBACK.items():
            regions.setdefault(name, list(cells))
        return regions

    def _region_contains_or_adjacent(self, position: Cell, cells: list[Cell]) -> bool:
        return any(position == cell or chebyshev(position, cell) == 1 for cell in cells)

    def _verdict(self, position: Cell, landmark: str) -> str:
        cells = self._all_regions().get(landmark)
        if cells is not None and self._region_contains_or_adjacent(position, cells):
            return "truth"
        return "lie"

    def _cap(self, text: str) -> str:
        """Truncate to the CONFIGURED max_words (never a hard-coded default)."""
        words = text.split()
        if len(words) <= self.max_words:
            return text
        return " ".join(words[: self.max_words])
