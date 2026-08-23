"""Typed contracts for the optional hint-text seam (T027, ADR-010).

Local deterministic code owns the claim, the destination landmark, and the
verdict (STRAT-008). A ``TextProvider``, if present, supplies wording only:
it receives an allowlisted request (role, arena, planned landmark, claim,
style, word cap -- nothing private) and returns text plus usage/provider/
model metadata. It never returns a verdict, action, barrier, target, score,
or legality, and no code path reads one from it (closes F-12).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Literal, Protocol, runtime_checkable

from common.domain.scoring import Role

Claim = Literal["truth", "lie"]

#: Sentinel claim for a position that belongs to no truth-compatible
#: landmark region. Carries no landmark and never reaches the provider.
NON_CLAIM = "non_claim"


class FallbackReason(Enum):
    """Why the plan's deterministic template text was used instead of a
    provider reply. Recorded on every fallback path -- never a silent pass.
    """

    NO_PROVIDER = "no_provider"
    NON_CLAIM = "non_claim"
    TIMEOUT = "timeout"
    EXCEPTION = "exception"
    MALFORMED = "malformed"
    INVALID_TEXT = "invalid_text"


@dataclass(frozen=True, slots=True)
class HintRenderRequest:
    """The provider privacy allowlist. Nothing else may be sent (ADR-010)."""

    role: Role
    arena: str
    target_landmark: str
    claim: Claim
    max_words: int
    style: str = "concise"


@dataclass(frozen=True, slots=True)
class TokenUsage:
    """Typed usage. ``None`` means unknown -- never inferred from text."""

    input_tokens: int | None
    output_tokens: int | None


@dataclass(frozen=True, slots=True)
class ProviderReply:
    """Wording only: no verdict/action/barrier/target/score/legality field."""

    text: str
    usage: TokenUsage
    provider: str
    model: str


@runtime_checkable
class TextProvider(Protocol):
    """Provider-neutral wording seam. Never on the movement path (NG-003)."""

    def render(
        self, request: HintRenderRequest, *, deadline: float | None
    ) -> ProviderReply: ...


@dataclass(frozen=True, slots=True)
class HintPlan:
    """Local deterministic plan, fixed before any provider call.

    ``claim`` is ``"truth"``, ``"lie"``, or ``NON_CLAIM``. ``NON_CLAIM``
    always carries ``target_landmark=None``: no landmark is fabricated for a
    position that belongs to no truth-compatible region.
    """

    claim: str
    target_landmark: str | None
    fallback_text: str


@dataclass(frozen=True, slots=True)
class HintResult:
    """The sealed outcome of one hint render: text, verdict, and audit trail."""

    text: str
    verdict: str
    fallback_reason: FallbackReason | None
    usage: TokenUsage
