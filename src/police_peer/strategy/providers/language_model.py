"""Optional LLM hint providers (T027, P2): OpenAI + Ollama.

Implements ``strategy.hints.TextProvider``. NEVER on the movement path
(STRAT-008, NG-003): ``generate`` only produces free-form hint text from an
already-locked action; any failure/None falls back to the deterministic
template (CT-02). Every live call goes through the single
``ExternalApiGatekeeper`` (4.5). ``claude_cli``/``claude_api`` have no OpenAI
analog and are dropped (deviation recorded in T027). Stdlib-only: ``template``
mode stays dependency-free; the OpenAI branch imports no SDK.
"""

from __future__ import annotations

import logging
import os

from common.domain.board import Cell, chebyshev
from police_peer.belief.hints import parse_landmarks
from police_peer.infra.external_api_gatekeeper import (
    ExternalApiGatekeeper,
    GatekeeperConfig,
)

logger = logging.getLogger(__name__)

DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
DEFAULT_OLLAMA_URL = "http://localhost:11434/api/generate"


def _system_prompt(role, arena: str, max_words: int) -> str:
    """System prompt pinning the arena + word cap (reference behaviour)."""
    who = "THIEF" if str(role).lower() == "thief" else "COP"
    area = arena or "an unnamed city"
    return (
        f"You are a witty {who} in a cop-and-thief chase set in {area}. Say "
        f'somewhere in {area}, no more than {max_words} words. You MAY lie about '
        f"where you are. Reply with STRICT JSON only: "
        f'{{"message": "<taunt>", "verdict": "truth|lie", '
        f'"reasoning": "<one clause; optional>"}}'
    )


def _verdict_for(message: str, position: Cell, arena: str) -> str:
    """Local truth/lie rule (FR-P6): 'truth' iff the asserted landmark region
    contains (or is Chebyshev-adjacent to) the position. Rule-computed, never
    trusted from the wire (4.4)."""
    matched = parse_landmarks(message, arena, 7)
    if not matched:
        return "truth"
    if any(position == c or chebyshev(position, c) == 1 for c in matched):
        return "truth"
    return "lie"


def _apply_cap(text: str, max_words: int) -> str:
    """Truncate to the negotiated word cap (post-processing, before the wire)."""
    words = text.split()
    return text if len(words) <= max_words else " ".join(words[:max_words])


class OpenAIProvider:
    """OpenAI Chat Completions provider (stdlib REST; key from env at runtime)."""

    uses_llm = True

    def __init__(
        self,
        model: str = DEFAULT_OPENAI_MODEL,
        every_n_steps: int = 1,
        gatekeeper: ExternalApiGatekeeper | None = None,
    ) -> None:
        self.model = model
        self.every_n_steps = max(1, int(every_n_steps))
        self.gatekeeper = gatekeeper or ExternalApiGatekeeper(GatekeeperConfig())
        self._turn = 0

    def generate(self, role, position, arena, max_words, deadline):
        self._turn += 1
        if self._turn % self.every_n_steps != 0:
            return None
        system = _system_prompt(role, arena, int(max_words))
        api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not api_key:
            return None

        def ask():
            from police_peer.strategy.providers.transports import chat_completion

            return chat_completion(
                api_key, self.model, system, 0.4, int(max_words), deadline,
            )

        try:
            raw = self.gatekeeper.execute(ask)
        except Exception:  # noqa: BLE001 — CT-02 failure behaviour
            return None
        return _make_result(raw, position, arena, max_words)


class OllamaProvider:
    """Local-model provider via the Ollama HTTP API (stdlib, free, no key).

    Mirrors the reference's ``ollama`` branch within the OpenAI family since
    ``claude_*`` has no OpenAI analog (see module docstring).
    """

    uses_llm = True

    def __init__(
        self,
        model: str = "llama3.2",
        url: str = DEFAULT_OLLAMA_URL,
        every_n_steps: int = 1,
        gatekeeper: ExternalApiGatekeeper | None = None,
    ) -> None:
        self.model = model
        self.url = url
        self.every_n_steps = max(1, int(every_n_steps))
        self.gatekeeper = gatekeeper or ExternalApiGatekeeper(GatekeeperConfig())
        self._turn = 0

    def generate(self, role, position, arena, max_words, deadline):
        self._turn += 1
        if self._turn % self.every_n_steps != 0:
            return None
        system = _system_prompt(role, arena, int(max_words))

        def ask():
            from police_peer.strategy.providers.transports import ollama_ask

            return ollama_ask(self.model, self.url, system, deadline)

        try:
            raw = self.gatekeeper.execute(ask)
        except Exception:  # noqa: BLE001 — CT-02 failure behaviour
            return None
        return _make_result(raw, position, arena, max_words)


def resolve_text_provider(config, gatekeeper=None):
    """Build a provider from the (private) ``[trash_talk]`` block, else None
    (template default). ``openai_api`` needs ``OPENAI_API_KEY`` at runtime;
    without it (or for unknown providers / ``template``) it degrades to None so
    the HintWriter uses the free deterministic template. Mirrors the reference
    ``resolve_trash_talk``."""
    tt = config.get("trash_talk") if config else None
    if not isinstance(tt, dict):
        return None
    provider = str(tt.get("provider", "template")).strip().lower()
    every = int(tt.get("every_n_steps", 1))
    model = str(tt.get("model", "")).strip()

    if provider == "openai_api":
        if not os.environ.get("OPENAI_API_KEY", "").strip():
            logger.warning("openai_api selected but OPENAI_API_KEY unset; using template")
            return None
        return OpenAIProvider(model=model or DEFAULT_OPENAI_MODEL,
                              every_n_steps=every, gatekeeper=gatekeeper)
    if provider == "ollama":
        url = str(tt.get("ollama_url", DEFAULT_OLLAMA_URL))
        return OllamaProvider(model=model or "llama3.2", url=url,
                              every_n_steps=every, gatekeeper=gatekeeper)
    if provider == "template":
        return None
    logger.warning("unknown trash_talk.provider %r; using template", provider)
    return None


def _make_result(raw, position, arena, max_words):
    """Strict-JSON contract -> dict, or None on any unusable reply (template)."""
    from police_peer.strategy.providers.transports import parse_reply

    parsed = parse_reply(raw)
    if parsed is None:
        return None
    message = parsed.get("message", "").strip()
    if not message:
        return None
    return {
        "message": _apply_cap(message, max_words),
        "verdict": _verdict_for(message, position, arena),
        "reasoning": parsed.get("reasoning", "").strip(),
    }
