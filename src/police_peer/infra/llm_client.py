"""Provider-neutral completion client seam (T049, ADR-010).

``CompletionClient`` is the one-method injection point a caller (e.g.
``LanguageModelAdapter`` in ``llm_provider.py``) uses to reach *some* text
completion service. Nothing here names a vendor, imports a vendor SDK, or
reads an environment variable -- that composition happens only once T050's
gate (PLANQ-003) resolves. ``RawCompletion`` is the untrusted shape a client
implementation returns; ``llm_provider.py`` is solely responsible for
validating and normalizing it into the sealed ``ProviderReply`` (T027).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

__all__ = ["CompletionClient", "RawCompletion"]


@dataclass(frozen=True, slots=True)
class RawCompletion:
    """Untrusted response shape from an injected ``CompletionClient``.

    Token fields are typed loosely (``object``) on purpose: a misbehaving or
    malformed client may hand back booleans, negative numbers, floats, or
    strings here, and ``llm_provider.py`` must be able to reject every one
    of those explicitly rather than coercing them.
    """

    text: object
    provider: str
    model: str
    input_tokens: object = None
    output_tokens: object = None


@runtime_checkable
class CompletionClient(Protocol):
    """One-method seam: a prompt in, a raw completion out. No vendor here."""

    def complete(self, prompt: str, *, deadline: float | None) -> RawCompletion: ...
