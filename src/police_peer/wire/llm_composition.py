"""Production composition root for the optional OpenRouter wording provider."""

from __future__ import annotations

import os
import time
from collections.abc import Mapping

from common.config import ConfigError
from police_peer.infra.external_api_gatekeeper import ExternalApiGatekeeper
from police_peer.infra.gatekeeper_types import GatekeeperConfig
from police_peer.infra.llm_client import CompletionClient
from police_peer.infra.llm_provider import LanguageModelAdapter
from police_peer.infra.openrouter_client import DEFAULT_BASE_URL, OpenRouterClient
from police_peer.strategy.hint_types import TextProvider
from police_peer.wire.identity_config import LlmSettings


def compose_text_provider(
    settings: LlmSettings,
    shared_config: Mapping[str, object],
    *,
    environment: Mapping[str, str] | None = None,
    completion_client: CompletionClient | None = None,
    gatekeeper: ExternalApiGatekeeper | None = None,
) -> TextProvider | None:
    """Build production dependencies once; template mode allocates no client or Gatekeeper."""
    if settings.provider == "template":
        return None
    if settings.provider != "openrouter":
        raise ConfigError(f"unsupported LLM provider {settings.provider!r}")

    env = os.environ if environment is None else environment
    api_key = str(env.get("OPENROUTER_API_KEY", "")).strip()
    if not api_key:
        raise ConfigError("OPENROUTER_API_KEY is required when provider='openrouter'")
    if not settings.model or settings.model == "template":
        raise ConfigError("[llm].model is required when provider='openrouter'")
    base_url = str(env.get("OPENROUTER_BASE_URL", DEFAULT_BASE_URL)).strip() or DEFAULT_BASE_URL
    try:
        client = completion_client or OpenRouterClient(
            api_key=api_key,
            model=settings.model,
            provider_slug=settings.provider_slug,
            base_url=base_url,
            max_output_tokens=settings.max_output_tokens,
        )
    except ValueError as exc:
        raise ConfigError(str(exc)) from None
    service_gatekeeper = gatekeeper or ExternalApiGatekeeper(
        _gatekeeper_config(shared_config), time_provider=time.monotonic,
    )
    return LanguageModelAdapter(client, service_gatekeeper)


def _gatekeeper_config(shared: Mapping[str, object]) -> GatekeeperConfig:
    raw = shared.get("rate_limiter_gatekeeper", {})
    block = raw if isinstance(raw, Mapping) else {}
    return GatekeeperConfig(
        requests_per_minute=int(block.get("requests_per_minute", 30)),
        bucket_capacity=int(block.get("requests_per_minute", 30)),
        concurrent_requests=max(2, int(block.get("concurrent_requests", 2))),
        queue_depth=int(block.get("queue_depth", 100)),
        max_retries=min(1, max(0, int(block.get("max_retries", 1)))),
        retry_backoff_sec=float(block.get("retry_backoff_sec", 0.5)),
        reporting_reserved_slots=1,
    )
