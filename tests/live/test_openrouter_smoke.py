"""One opt-in, token-bounded request through the production OpenRouter composition."""

from __future__ import annotations

import json
import os
import random
import time

import pytest

from common.domain.scoring import Role
from police_peer.infra.openrouter_client import OpenRouterClient
from police_peer.strategy.hint_types import HintRenderRequest
from police_peer.strategy.hints import HintWriter
from police_peer.wire.identity_config import LlmSettings
from police_peer.wire.llm_composition import compose_text_provider

MODEL = "deepseek/deepseek-v4-flash-0731:nitro"
MAX_INPUT_TOKENS = 99
MAX_OUTPUT_TOKENS = 8

pytestmark = [
    pytest.mark.live_openrouter,
    pytest.mark.skipif(
        os.environ.get("RUN_LIVE_OPENROUTER_TESTS") != "1"
        or not os.environ.get("OPENROUTER_API_KEY"),
        reason="requires explicit live opt-in and an existing OPENROUTER_API_KEY",
    ),
]


def test_one_bounded_production_composition_request() -> None:
    model = os.environ.get("OPENROUTER_SMOKE_MODEL", MODEL)
    provider_slug = os.environ.get("OPENROUTER_SMOKE_PROVIDER") or None
    assert (model, provider_slug) == (MODEL, None), "unapproved smoke override refused"
    settings = LlmSettings(
        "openrouter", model, provider_slug, 30.0, MAX_OUTPUT_TOKENS, 1,
    )
    text_provider = compose_text_provider(settings, {}, environment=os.environ)
    assert text_provider is not None
    request = HintRenderRequest(
        role=Role.POLICE, arena="New York", target_landmark="Central Park",
        claim="truth", max_words=8,
    )
    reply = text_provider.render(request, deadline=time.monotonic() + 30.0)
    validator = HintWriter(Role.POLICE, random.Random(0), "New York", 8)
    assert validator._valid_text(reply.text, "Central Park")
    assert reply.usage.input_tokens is not None and reply.usage.input_tokens < 100
    assert reply.usage.output_tokens is not None and reply.usage.output_tokens <= 8
    client = text_provider._client
    assert isinstance(client, OpenRouterClient) and client.request_count <= 2
    print(json.dumps({
        "model": reply.model, "provider": reply.provider,
        "input_tokens": reply.usage.input_tokens,
        "output_tokens": reply.usage.output_tokens,
        "request_count": client.request_count,
        "maximum_output_tokens": MAX_OUTPUT_TOKENS,
    }, sort_keys=True))
