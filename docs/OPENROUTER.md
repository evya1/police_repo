# OpenRouter hint-wording API

OpenRouter is an optional wording layer. Deterministic Python code selects every move,
barrier, target landmark, claim, verdict, score, and legality result before a provider is
called. Provider output can replace only the human-readable hint sentence.

The default `template` provider is offline, uses zero tokens, and constructs no HTTP client.
`openrouter` is an explicit opt-in.

## File map

| File | Responsibility |
| --- | --- |
| `src/police_peer/infra/openrouter_client.py` | OpenRouter HTTP transport, deadline conversion, response extraction, and sanitized failure classes. |
| `src/police_peer/wire/llm_composition.py` | Production configuration/environment boundary and dependency composition. |
| `src/police_peer/reporting/runtime_artifacts.py` | Stable local summary writer extracted from the CLI runner. |
| `src/police_peer/wire/startup.py` | Shared startup validation used before provider composition. |
| `tests/contract/test_openrouter_client.py` | In-memory HTTP success, usage, deadline, cap, privacy, and failure contracts. |
| `tests/integration/test_llm_production.py` | SDK/CLI composition, deterministic fallback, ledger, and secret-persistence coverage. |
| `tests/live/test_openrouter_smoke.py` | Explicitly opted-in, cost-bounded production-composition smoke request. |
| `tests/unit/wire/test_llm_config.py` | Offline default and fail-fast configuration tests, including live opt-in without a key. |

## Configuration

Private TOML selects the provider; credentials never belong in TOML:

```toml
[llm]
provider = "openrouter" # template | openrouter
model = "deepseek/deepseek-v4-flash-0731:nitro"
# provider_slug = "novita" # optional explicit pin; omit for Nitro routing
step_deadline_seconds = 30
max_output_tokens = 32
every_n_steps = 1
```

Export credentials in the process environment:

```sh
export OPENROUTER_API_KEY='<your key>'
export OPENROUTER_BASE_URL='https://openrouter.ai/api/v1' # optional default
```

The application does **not** load `.env` automatically. Export variables in the shell or
inject an environment mapping through the SDK. `RUN_LIVE_OPENROUTER_TESTS` and the smoke
model/provider variables affect tests only.

## Public composition API

`police_peer.wire.llm_composition.compose_text_provider(...)` is the only production
environment-reading boundary:

```python
compose_text_provider(
    settings: LlmSettings,
    shared_config: Mapping[str, object],
    *,
    environment: Mapping[str, str] | None = None,
    completion_client: CompletionClient | None = None,
    gatekeeper: ExternalApiGatekeeper | None = None,
) -> TextProvider | None
```

Inputs:

- `settings`: validated private `[llm]` values.
- `shared_config`: supplies Gatekeeper rate, concurrency, queue, and retry limits.
- `environment`: optional SDK injection; `None` means `os.environ`.
- `completion_client` and `gatekeeper`: optional typed test/application injections.

Output and startup behavior:

- `template` returns `None` without reading credentials or constructing network objects.
- `openrouter` returns a `LanguageModelAdapter` implementing `TextProvider`.
- Missing keys or models and invalid limits raise `ConfigError` before transport startup.
  `provider_slug` is optional.

`police_peer.sdk.create_peer(...)` exposes the same optional `environment`,
`completion_client`, `gatekeeper`, `text_provider`, and `token_ledger` injection seams. Normal
CLI composition leaves them automatic; callers can inject fakes without introducing a second
HTTP path.

## HTTP client API

`police_peer.infra.openrouter_client.OpenRouterClient` implements `CompletionClient`:

```python
OpenRouterClient(
    *,
    api_key: str,
    model: str,
    provider_slug: str | None = None,
    base_url: str = "https://openrouter.ai/api/v1",
    max_output_tokens: int = 32,
    clock: Callable[[], float] = time.monotonic,
    opener: Callable[..., Any] = urllib.request.urlopen,
)

complete(prompt: str, *, deadline: float | None) -> RawCompletion
```

The constructor receives credentials directly and never reads the environment. `deadline` is
an absolute monotonic deadline; the request timeout is the smaller of its positive remaining
budget and 30 seconds. Expired deadlines make no request. Output is capped to 64 tokens by the
class and to the configured smaller value in normal composition.

The client sends `POST <base_url>/chat/completions` with:

- one user text message;
- the fixed model and output-token cap;
- temperature zero and reasoning explicitly disabled;
- no provider routing block when `provider_slug` is omitted, allowing Nitro to choose the
  fastest healthy provider;
- when `provider_slug` is explicit, routing is pinned to that slug, fallback is disabled,
  parameter support is required, and provider data collection is denied; and
- the key only in the bearer authorization header.

`RawCompletion` returns untrusted response fields:

```python
RawCompletion(
    text: object,
    provider: str,
    model: str,
    input_tokens: object | None,
    output_tokens: object | None,
)
```

OpenRouter `usage.prompt_tokens` and `usage.completion_tokens` map to the two token fields.
Missing usage remains `None`; it is never inferred or rewritten to zero. Supplied response
`model` and `provider` values are retained.

Sanitized client failures are classified as `OpenRouterAuthenticationError`,
`OpenRouterRateLimitError`, `OpenRouterTimeoutError`, `OpenRouterConnectionError`, or
`OpenRouterMalformedResponseError`. Exceptions contain neither prompts nor credentials.

## Wording input and output

`LanguageModelAdapter.render(request, deadline=...) -> ProviderReply` calls the client only
through `ExternalApiGatekeeper.execute(..., lane="llm")`.

`HintRenderRequest` is the prompt privacy allowlist:

| Field | Meaning |
| --- | --- |
| `role` | This peer's role. |
| `arena` | Public arena name. |
| `target_landmark` | Deterministically selected public landmark. |
| `claim` | Deterministically selected `truth` or `lie` claim. |
| `max_words` | Local validation limit. |
| `style` | Public wording style, default `concise`. |

Cells, grids, scent, belief, opponent data, legal moves, barriers, scores, and credentials have
no request fields and cannot enter the prompt.

Validated output is:

```python
ProviderReply(
    text: str,
    usage: TokenUsage,
    provider: str,
    model: str,
)
```

The text must be one bounded plain-text sentence containing exactly the planned landmark and
no coordinates, code fences, control characters, or other landmark. Any client, Gatekeeper,
usage, or validation failure selects deterministic template wording without changing the
already-selected move, barrier, target, claim, or verdict.

## Accounting and artifacts

`HintWriter.last_result` exposes the sealed `HintResult` immediately after a decision.
`BrainDrivenEngine` converts its `TokenUsage` into a `TokenEvent` and records it in the injected
`TokenLedger`.

- A template/no-call/skipped hint records known `0/0` usage.
- A dispatched call without reliable usage records unknown `None/None` usage.
- Replay result evidence includes per-sub-game and series token totals.
- Kit projection uses ledger totals; unknown counted usage cannot be projected as zero.
- Counted play fails closed when any required counted usage is unknown.

`police_peer.reporting.runtime_artifacts.write_artifacts(...)` writes the stable local series
summary. Replay and kit publishers receive token accounting separately so this pre-existing
summary schema does not change.

## Tests without a real key

Normal tests never make a live call:

```sh
uv run pytest
```

Mocked OpenRouter and composition tests can be run on demand with no key:

```sh
uv run pytest --no-cov \
  tests/contract/test_openrouter_client.py \
  tests/integration/test_llm_production.py \
  tests/unit/wire/test_llm_config.py
```

Selecting the live marker while deliberately providing no key is also safe: the smoke test is
skipped and sends zero requests.

```sh
OPENROUTER_API_KEY= RUN_LIVE_OPENROUTER_TESTS=1 \
  uv run pytest --no-cov -m live_openrouter
```

The real smoke test requires both an existing key and explicit opt-in. It performs one
production-composition render with at most one 429 retry:

```sh
RUN_LIVE_OPENROUTER_TESTS=1 uv run pytest --no-cov -m live_openrouter
```
