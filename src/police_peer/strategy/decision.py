"""Decision contract — frozen dataclass for the CT-02 response.

Shared core (mirrors thief_repo identically modulo import path and role constant).
"""

from __future__ import annotations

from dataclasses import dataclass

from common.domain.board import Cell

from .hint_types import FallbackReason, TokenUsage


@dataclass(frozen=True)
class Decision:
    """The CT-02 response: one legal action + the verbal phase + audit metadata.

    Invariants: `action` is a member of this turn's CT-01 legal set;
    `barrier_cell` is None for THIEF (role guard, M-04) and, for POLICE,
    requires action == "STAY" and membership in barrier_targets() under quota;
    `hint` is at most hint_max_words words; `verdict` is sealed for audit.
    The serializable projection (action, barrier_cell as [r,c] | None, hint,
    verdict) feeds the canonical-JSON commit preimage (SPEC section 2) via C03.
    `fallback_reason` and `usage` are sealed hint-text audit metadata (T027,
    SEC-009); defaulted so the constructor stays source-compatible.
    """

    action: str
    barrier_cell: Cell | None = None
    hint: str = ""
    verdict: str = "truth"  # "truth" | "lie"
    fallback: bool = False  # True when forced STAY (no legal orthogonal move)
    reasoning: str = ""  # "" for template mode
    prompt_text: str = ""  # sealed (prompt_discussion) for audit; "" for template
    response_seconds: float = 0.0  # hint-phase timing metadata; never a decision input
    fallback_reason: FallbackReason | None = None  # sealed; None when the provider text was used
    usage: TokenUsage | None = None  # sealed; None when unknown (never inferred from text)
