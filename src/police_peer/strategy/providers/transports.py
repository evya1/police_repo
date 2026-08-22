"""Transport helpers for the optional LLM providers (T027): stdlib HTTP askers.

Split out of ``language_model.py`` to stay within the line-cap. Pure stdlib —
no ``openai``/``anthropic`` dependency. ``_chat_completion`` posts to the
OpenAI Chat Completions API; ``_ollama_ask`` posts to a local Ollama endpoint.
The API key is passed at call time only and never logged.
"""

from __future__ import annotations

import json
import urllib.request

_BASE_URL = "https://api.openai.com/v1/chat/completions"


def _extract_json(text: str) -> str:
    """Pull the JSON object out of a reply (tolerates ``` fences / prose)."""
    start, end = text.find("{"), text.rfind("}")
    return text[start:end + 1] if 0 <= start < end else text


def parse_reply(raw: str) -> dict | None:
    """Strict-JSON parse of a model reply -> {"message","verdict","reasoning"}."""
    try:
        data = json.loads(_extract_json(raw))
    except Exception:  # noqa: BLE001 — malformed reply => None (template)
        return None
    if not isinstance(data, dict):
        return None
    message = str(data.get("message", "")).strip()
    if not message:
        return None
    return {
        "message": message,
        "verdict": str(data.get("verdict", "truth")),
        "reasoning": str(data.get("reasoning", "")).strip(),
    }


def chat_completion(api_key, model, system, temperature, max_words, deadline,
                    base_url=_BASE_URL):
    """One OpenAI Chat Completions call (stdlib REST, no SDK)."""
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": system}],
        "temperature": temperature,
        "max_tokens": max(16, int(max_words) * 20),
    }
    request = urllib.request.Request(
        base_url, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {api_key}"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=deadline or 30) as response:
        body = json.loads(response.read())
    try:
        return body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError("empty OpenAI reply") from exc


def ollama_ask(model, url, prompt, deadline):
    """One local Ollama generate call (stdlib only, free)."""
    payload = {"model": model, "prompt": prompt, "stream": False, "format": "json"}
    request = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=deadline or 30) as response:
        return json.loads(response.read())["response"]
