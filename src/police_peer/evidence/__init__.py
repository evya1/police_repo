"""Honest per-series evidence: Step-0 declaration and token accounting (T013).

Two independent concerns live here:

- ``tokens``: append-only, idempotent token-usage accounting that never turns
  ``unknown`` into ``0`` and never infers counts from text.
- ``step_zero``: the signed reproducibility declaration required before the
  first move, built through an injected signing seam.

Neither module reads the environment, calls a provider, or decides move
legality -- both are pure evidence, never game authority (ADR-010).
"""

from __future__ import annotations

from police_peer.evidence.runtime_summary import RuntimeSummary, collect_runtime_summary
from police_peer.evidence.step_zero import (
    MissingCodeRevisionError,
    MissingConfigDigestError,
    MissingSigningCredentialError,
    SignedStepZero,
    StepZeroDeclaration,
    StepZeroError,
    build_signed_step_zero,
    verify_signed_step_zero,
)
from police_peer.evidence.token_ledger import (
    CountedPlayIneligibleError,
    DuplicateTokenEventError,
    TokenLedger,
    TokenTotal,
    assert_counted_eligible,
)
from police_peer.evidence.tokens import (
    InvalidTokenCountError,
    TokenAccountingError,
    TokenEvent,
    UsageStatus,
    event_from_hint_result,
    status_for_counts,
)

__all__ = [
    "CountedPlayIneligibleError",
    "DuplicateTokenEventError",
    "InvalidTokenCountError",
    "MissingCodeRevisionError",
    "MissingConfigDigestError",
    "MissingSigningCredentialError",
    "RuntimeSummary",
    "SignedStepZero",
    "StepZeroDeclaration",
    "StepZeroError",
    "TokenAccountingError",
    "TokenEvent",
    "TokenLedger",
    "TokenTotal",
    "UsageStatus",
    "assert_counted_eligible",
    "build_signed_step_zero",
    "collect_runtime_summary",
    "event_from_hint_result",
    "status_for_counts",
    "verify_signed_step_zero",
]
