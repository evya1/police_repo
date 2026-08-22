"""HintWriter — template-default verbal layer + TextProvider seam.

Shared core (mirrors thief_repo identically modulo import path and role constant).
Landmark names imported from belief.hints.LANDMARK_CELLS (SD-B3).
"""

from __future__ import annotations

import random
from typing import Protocol

from common.domain.board import Cell, chebyshev
from common.domain.scoring import Role
from police_peer.belief.hints import GENERIC_FALLBACK, LANDMARK_CELLS


class TextProvider(Protocol):
    """Provider-neutral seam for the optional LLM adapter (T027, P2, gated by
    PLANQ-003/004). NEVER on the movement path (STRAT-008, NG-003)."""

    def generate(
        self,
        role: Role,
        position: Cell,
        arena: str,
        max_words: int,
        deadline: float | None,
    ) -> dict[str, str] | None:
        """Strict JSON {"message", "verdict", "reasoning"}, or None on any
        failure/timeout/unparseable reply (template fallback then applies).
        """


class HintWriter:
    """Template-default verbal layer (STRAT-008). Landmark names from
    belief.hints.LANDMARK_CELLS (SD-B3 — one table, both directions).
    """

    # Template banks per role: 3–4 truth/lie variants each.
    _TEMPLATES: dict[Role, dict[str, list[str]]] = {
        Role.POLICE: {
            "truth": [
                "I'm patrolling the {landmark} area.",
                "You'll find me near {landmark}.",
                "I'm guarding the {landmark} district.",
                "The {landmark} sector is my post.",
            ],
            "lie": [
                "I'm somewhere near {landmark}.",
                "Look for me in the {landmark} zone.",
                "I've been around {landmark} today.",
                "My location is close to {landmark}.",
            ],
        },
        Role.THIEF: {
            "truth": [
                "I'm in the {landmark} area.",
                "You'll find me near {landmark}.",
                "I'm hiding around {landmark}.",
                "The {landmark} district is where I am.",
            ],
            "lie": [
                "I'm somewhere near {landmark}.",
                "Look for me in the {landmark} zone.",
                "I've been around {landmark} today.",
                "My location is close to {landmark}.",
            ],
        },
    }

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

    def say(self, position: Cell, *, deadline: float | None = None) -> tuple[str, str]:
        """(hint, verdict). Template mode (default, zero tokens).

        - lie roll: rng.random() < 0.4 (reference behaviour, seeded);
        - truth: assert a landmark region containing (or Chebyshev-adjacent to)
          `position`; none applicable ⇒ generic non-landmark line (no claim);
        - lie: assert a landmark region NOT containing (or adjacent to) it;
        - verdict RULE-COMPUTED: "truth" iff the asserted region contains or is
          Chebyshev-adjacent to `position` — the role knows its own position,
          so the verdict is always well-defined and audit-consistent;
        - _cap truncates to max_words (for LLM providers the arena + cap also
          enter the system prompt, reference behaviour).
        Provider mode (T027): call with deadline; any failure ⇒ template.
        """
        # Provider mode (T027 seam — implementation deferred, SD-P6).
        if self.provider is not None:
            try:
                result = self.provider.generate(
                    self.role, position, self.arena, self.max_words, deadline,
                )
                if result is not None:
                    return self._cap(result.get("message", "")), result.get("verdict", "truth")
            except Exception:  # noqa: BLE001 — CT-02 failure behaviour
                pass

        # Template mode.
        want_lie = self.rng.random() < 0.4
        landmark = self._pick_landmark(position, want_lie)
        if landmark is None:
            return self._generic_line(), "truth"
        templates = self._TEMPLATES[self.role]["lie" if want_lie else "truth"]
        template = self.rng.choice(templates)
        hint = template.format(landmark=landmark)
        verdict = self._verdict(position, landmark)
        return self._cap(hint), verdict

    def _pick_landmark(self, position: Cell, want_lie: bool) -> str | None:
        """Pick a landmark region name. Returns None if no suitable region."""
        arena_landmarks = LANDMARK_CELLS.get(self.arena, {})
        truth_regions = [
            name
            for name, cells in arena_landmarks.items()
            if self._region_contains_or_adjacent(position, cells)
        ]
        lie_regions = [
            name
            for name, cells in arena_landmarks.items()
            if not self._region_contains_or_adjacent(position, cells)
        ]
        candidates = truth_regions if not want_lie else lie_regions
        if not candidates:
            # Try generic fallback.
            if not want_lie:
                return self.rng.choice(list(GENERIC_FALLBACK.keys()))
            return None
        return self.rng.choice(candidates)

    def _region_contains_or_adjacent(self, position: Cell, cells: list[Cell]) -> bool:
        """True if position is in the region or Chebyshev-adjacent to it."""
        return any(position == cell or chebyshev(position, cell) == 1 for cell in cells)

    def _verdict(self, position: Cell, landmark: str) -> str:
        """Compute verdict: 'truth' iff the asserted region contains or is
        Chebyshev-adjacent to the position.
        """
        arena_landmarks = LANDMARK_CELLS.get(self.arena, {})
        cells = arena_landmarks.get(landmark) or GENERIC_FALLBACK.get(landmark.lower())
        if cells is not None and self._region_contains_or_adjacent(position, cells):
            return "truth"
        return "lie"

    def _generic_line(self) -> str:
        """Generic non-landmark hint line when no landmark applies."""
        return "I'm somewhere in the city."

    @staticmethod
    def _cap(text: str, max_words: int | None = None) -> str:
        """Truncate to max_words words (default 15 from shared config)."""
        limit = max_words or 15
        words = text.split()
        if len(words) <= limit:
            return text
        return " ".join(words[:limit])
