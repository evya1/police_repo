"""Small OpenRouter Chat Completions transport implementing ``CompletionClient``."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any

from police_peer.infra.llm_client import RawCompletion

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
MAX_OUTPUT_TOKENS = 3200
MAX_REQUEST_SECONDS = 30.0
_MAX_RESPONSE_BYTES = 256_000


class OpenRouterError(Exception):
    """Base class for sanitized OpenRouter transport failures."""


class OpenRouterAuthenticationError(OpenRouterError):
    """The supplied credential was rejected."""


class OpenRouterRateLimitError(OpenRouterError):
    """OpenRouter returned HTTP 429; the Gatekeeper may retry it once."""

    status_code = 429


class OpenRouterTimeoutError(TimeoutError, OpenRouterError):
    """The monotonic deadline expired or the request timed out."""


class OpenRouterConnectionError(ConnectionError, OpenRouterError):
    """The service could not be reached or returned a non-auth HTTP failure."""


class OpenRouterMalformedResponseError(OpenRouterError):
    """A successful HTTP response did not contain a valid text completion."""


class OpenRouterClient:
    """Credential-injected, dependency-free OpenRouter completion client."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        provider_slug: str,
        base_url: str = DEFAULT_BASE_URL,
        max_output_tokens: int = 32,
        clock: Callable[[], float] = time.monotonic,
        opener: Callable[..., Any] = urllib.request.urlopen,
    ) -> None:
        if not api_key or not model or not provider_slug:
            raise ValueError("OpenRouter credentials, model, and provider slug are required")
        if not 1 <= max_output_tokens <= MAX_OUTPUT_TOKENS:
            raise ValueError(f"max_output_tokens must be between 1 and {MAX_OUTPUT_TOKENS}")
        self._api_key = api_key
        self.model = model
        self.provider_slug = provider_slug
        self.max_output_tokens = max_output_tokens
        self._url = _completion_url(base_url)
        self._clock = clock
        self._opener = opener
        self.request_count = 0

    def complete(self, prompt: str, *, deadline: float | None) -> RawCompletion:
        """Send one bounded request and return the provider's untrusted raw fields."""
        timeout = self._remaining_timeout(deadline)
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": self.max_output_tokens,
            "temperature": 0,
            "reasoning": {"enabled": False},
            "provider": {
                "only": [self.provider_slug],
                "allow_fallbacks": False,
                "require_parameters": True,
                "data_collection": "deny",
            },
        }
        request = urllib.request.Request(
            self._url,
            data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        self.request_count += 1
        try:
            with self._opener(request, timeout=timeout) as response:
                raw_body = response.read(_MAX_RESPONSE_BYTES + 1)
        except urllib.error.HTTPError as exc:
            self._raise_http_error(exc.code)
        except TimeoutError as exc:
            raise OpenRouterTimeoutError("OpenRouter request timed out") from exc
        except (urllib.error.URLError, OSError) as exc:
            if isinstance(getattr(exc, "reason", None), TimeoutError):
                raise OpenRouterTimeoutError("OpenRouter request timed out") from exc
            raise OpenRouterConnectionError("OpenRouter connection failed") from exc
        if len(raw_body) > _MAX_RESPONSE_BYTES:
            raise OpenRouterMalformedResponseError("OpenRouter response exceeded the size limit")
        return self._parse_response(raw_body)

    def _remaining_timeout(self, deadline: float | None) -> float:
        if deadline is None:
            return MAX_REQUEST_SECONDS
        remaining = deadline - self._clock()
        if remaining <= 0:
            raise OpenRouterTimeoutError("OpenRouter deadline expired before request start")
        return min(remaining, MAX_REQUEST_SECONDS)

    @staticmethod
    def _raise_http_error(status: int) -> None:
        if status in (401, 403):
            raise OpenRouterAuthenticationError("OpenRouter authentication failed") from None
        if status == 429:
            raise OpenRouterRateLimitError("OpenRouter rate limit exceeded") from None
        if status in (408, 504):
            raise OpenRouterTimeoutError("OpenRouter request timed out") from None
        raise OpenRouterConnectionError(f"OpenRouter HTTP request failed with status {status}")

    def _parse_response(self, raw_body: bytes) -> RawCompletion:
        try:
            body = json.loads(raw_body)
            text = body["choices"][0]["message"]["content"]
            if not isinstance(body, dict) or not isinstance(text, str) or not text.strip():
                raise TypeError
            usage = body.get("usage")
            if usage is not None and not isinstance(usage, dict):
                raise TypeError
        except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
            raise OpenRouterMalformedResponseError("OpenRouter returned a malformed response") from exc
        return RawCompletion(
            text=text,
            provider=body.get("provider") or self.provider_slug,
            model=body.get("model") or self.model,
            input_tokens=usage.get("prompt_tokens") if usage is not None else None,
            output_tokens=usage.get("completion_tokens") if usage is not None else None,
        )


def _completion_url(base_url: str) -> str:
    base = base_url.strip().rstrip("/")
    if not base.startswith(("https://", "http://")):
        raise ValueError("OPENROUTER_BASE_URL must be an HTTP(S) URL")
    return base if base.endswith("/chat/completions") else f"{base}/chat/completions"
