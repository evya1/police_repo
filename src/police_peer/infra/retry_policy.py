"""Pure retry classification and backoff scheduling for the central Gatekeeper.

Stateless by design: the Gatekeeper owns the clock, the sleeper, and the
deadline math; this module only decides *whether* and *how long*.
"""

from __future__ import annotations

_NON_RETRYABLE_TYPE_NAMES = frozenset(
    {
        "DraftSubstitutionError",
        "AttachmentMissingError",
        "DuplicateSendError",
        "InvalidScopeError",
        "GmailTransmissionUncertainError",
    }
)


def is_hard_failure(exc: Exception) -> bool:
    """Return True for a typed caller failure that must propagate unwrapped.

    Identified by class name (to avoid the Gatekeeper importing caller
    modules) — these are never retried and never wrapped in ExternalCallError.
    """
    return exc.__class__.__name__ in _NON_RETRYABLE_TYPE_NAMES


def is_transient(exc: Exception) -> bool:
    """Classify `exc` as a transparent 429/rate-limit condition worth retrying."""
    status_code = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    if status_code == 429:
        return True
    message = str(exc).lower()
    return "429" in message or "rate" in message


def next_backoff(current_backoff: float, multiplier: float = 2.0) -> float:
    """Compute the next exponential backoff duration."""
    return current_backoff * multiplier


def has_budget_for(remaining: float | None, needed: float) -> bool:
    """Return True when there is no deadline, or enough budget remains for `needed`."""
    return remaining is None or remaining >= needed
