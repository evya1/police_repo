"""Provider-neutral adapter: allowlisted prompt -> Gatekeeper `llm` lane -> ProviderReply.

Implements LLM-06/LLM-07 (T049, ADR-010). Turns the T027 ``HintRenderRequest``
into a versioned, deterministic, plain-text prompt built only from its own
allowlisted fields (role, arena, planned landmark, claim, style, word cap --
never a cell, grid, scent, belief, legal move, or opponent datum). The
injected ``CompletionClient`` is reached exclusively through
``ExternalApiGatekeeper.execute(lane="llm", ...)`` using the caller's own
deadline, never a reset one. The raw reply is validated and normalized into
the frozen ``ProviderReply``; every rejection is a typed error the caller
(``HintWriter``) already maps to its deterministic fallback template.
"""

from __future__ import annotations

from police_peer.infra.external_api_gatekeeper import ExternalApiGatekeeper
from police_peer.infra.llm_client import CompletionClient, RawCompletion
from police_peer.strategy.hint_types import HintRenderRequest, ProviderReply, TokenUsage

__all__ = [
    "InvalidOutputTextError",
    "LanguageModelAdapter",
    "LlmAdapterError",
    "MalformedResponseError",
    "MalformedUsageError",
    "PROMPT_VERSION",
    "build_prompt",
]

#: Bumping this changes the prompt's wire shape; keep every prompt traceable
#: to the exact template version that produced it.
PROMPT_VERSION = "llm-hint-prompt/v1"

_MAX_TEXT_CHARS = 2000


class LlmAdapterError(Exception):
    """Base for typed T049 validation failures (ADR-010's fallback boundary).

    Every subclass is an ordinary ``Exception`` on purpose: ``HintWriter``'s
    existing ``except Exception`` fallback boundary (T027) already maps any
    of these to ``FallbackReason.EXCEPTION`` without needing to know this
    module exists.
    """


class MalformedResponseError(LlmAdapterError):
    """Raised when the injected client returns something other than a
    ``RawCompletion``."""


class MalformedUsageError(LlmAdapterError):
    """Raised when a raw usage count is a bool, negative, or not an int/None."""


class InvalidOutputTextError(LlmAdapterError):
    """Raised when the raw output text is not a string, is empty, or is
    oversized."""


def build_prompt(request: HintRenderRequest) -> str:
    """Deterministic, versioned, plain-text prompt from allowlisted fields only.

    Every line derives from a field already present on ``HintRenderRequest``
    (T027's privacy allowlist) -- no other attribute of the caller's state is
    reachable from here. Requests plain prose, not model-owned JSON.
    """
    return "\n".join((
        PROMPT_VERSION,
        f"role={request.role.value}; arena={request.arena}",
        f"landmark={request.target_landmark}; claim={request.claim}",
        f"style={request.style}; max_words={request.max_words}",
        "One plain sentence. Mention the landmark exactly. No JSON or code.",
    ))


def _normalize_count(value: object, field_name: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise MalformedUsageError(
            f"{field_name} must be an int or None, got {type(value).__name__}"
        )
    if value < 0:
        raise MalformedUsageError(f"{field_name} must be nonnegative, got {value}")
    return value


def _normalize_usage(raw: RawCompletion) -> TokenUsage:
    """Unknown usage stays ``None``; never inferred from the completion text."""
    return TokenUsage(
        input_tokens=_normalize_count(raw.input_tokens, "input_tokens"),
        output_tokens=_normalize_count(raw.output_tokens, "output_tokens"),
    )


def _normalize_text(raw_text: object) -> str:
    if not isinstance(raw_text, str):
        raise InvalidOutputTextError(
            f"completion text must be str, got {type(raw_text).__name__}"
        )
    if not raw_text.strip():
        raise InvalidOutputTextError("completion text is empty")
    if len(raw_text) > _MAX_TEXT_CHARS:
        raise InvalidOutputTextError(f"completion text exceeds {_MAX_TEXT_CHARS} characters")
    return raw_text


class LanguageModelAdapter:
    """Provider-neutral ``TextProvider``: no vendor import, no env lookup."""

    def __init__(self, client: CompletionClient, gatekeeper: ExternalApiGatekeeper) -> None:
        self._client = client
        self._gatekeeper = gatekeeper

    def render(self, request: HintRenderRequest, *, deadline: float | None) -> ProviderReply:
        """Build the allowlisted prompt, call the client via the `llm` lane,
        and normalize its reply. ``deadline`` is the caller's own turn
        deadline, passed through unchanged -- never reset or extended.
        """
        prompt = build_prompt(request)

        def _call() -> RawCompletion:
            return self._client.complete(prompt, deadline=deadline)

        raw = self._gatekeeper.execute(_call, lane="llm", deadline=deadline)
        if not isinstance(raw, RawCompletion):
            raise MalformedResponseError(
                f"client returned {type(raw).__name__}, expected RawCompletion"
            )
        text = _normalize_text(raw.text)
        usage = _normalize_usage(raw)
        return ProviderReply(text=text, usage=usage, provider=str(raw.provider), model=str(raw.model))
