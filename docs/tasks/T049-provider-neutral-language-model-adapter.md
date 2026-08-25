---
id: T049
status: done
priority: P2
task_type: component
component: C06
optional: true
implements:
  - STRAT-008
  - QR-008
context_files:
  - docs/components/C06-reporting-league/PRD.md
  - docs/components/C06-reporting-league/PLAN.md
  - docs/PRD_llm_provider.md
  - docs/PLAN_llm_provider.md
read_set: []
depends_on:
  - T027
  - T048
gates: []
parallel_safe: true
claimed_by:
claim_expires_at:
write_set:
  - src/police_peer/infra/llm_client.py
  - src/police_peer/infra/llm_provider.py
  - tests/unit/infra/test_llm_provider.py
  - tests/contract/test_llm_provider_contract.py
risk: medium
---

# T049 — Provider-neutral language model adapter

## Expected outcome

A vendor-neutral adapter turns a `HintRenderRequest` into a deterministic prompt, calls an injected
one-method client exclusively through the Gatekeeper's `llm` lane, and normalizes the response into
a frozen `ProviderReply`. No vendor SDK, no environment read, and no network fixture appear here.

## Requirements implemented

- `STRAT-008`
- `QR-008`

## Relevant context

Implements LLM-06 and LLM-07 of `docs/PRD_llm_provider.md`. REVIEW_FINDINGS **F-16**: provider usage
has no typed boundary and the existing hint result is a mutable `dict[str, str]`, so token totals
cannot be traced reliably into sealed evidence.

The selected vendor's transport is T050 and is separately gated by `PLANQ-003`.

## Constraints

- Edit only the declared write set.
- Define the one-method `CompletionClient` `Protocol` next to its consumer; no vendor import, no
  dependency addition, no environment lookup, no vendor name in this task.
- Reuse the strategy-owned request/reply types from T027 rather than redefining them.
- Every code and test file stays below 150 logical lines.
- No live external call in any test.

## Acceptance criteria

- [x] The prompt is versioned and deterministic, built only from allowlisted `HintRenderRequest`
      fields, and requests plain text rather than model-owned JSON semantics.
- [x] The injected client is called only via `ExternalApiGatekeeper.execute(lane="llm", ...)` with the
      passed deadline.
- [x] One client response normalizes into `ProviderReply` with provider and model identifiers and
      optional nonnegative token counts.
- [x] Booleans and negative usage values, and oversized or empty raw text, are rejected with typed
      adapter errors that `HintWriter` maps to a deterministic fallback.
- [x] Unknown usage stays `None`; token counts are never inferred from the text.
- [x] Contract tests run fake clients for success, timeout, 429 retry, missing usage, malformed types,
      and the privacy allowlist, and assert zero live network access.

## Verification

- `uv run pytest tests/unit/infra/test_llm_provider.py tests/contract/test_llm_provider_contract.py`
- `uv run ruff check src/police_peer/infra tests`
- `uv run python scripts/check_line_cap.py`

## Result and evidence

Implemented by a Sonnet 5 worker, reviewed and committed by the orchestrator on
`claude/replay-llm-completion-20260823` (2026-08-23).

`src/police_peer/infra/llm_client.py` (32 logical lines): the one-method `CompletionClient`
`Protocol` and `RawCompletion` — no vendor import, no environment lookup, no vendor name anywhere.
`src/police_peer/infra/llm_provider.py` (108 lines): `build_prompt` (versioned, deterministic,
allowlisted-fields-only, plain-text request), response normalization into T027's existing frozen
`ProviderReply`, and `LanguageModelAdapter`, which reuses T027's `HintRenderRequest`/`TokenUsage`/
`TextProvider` from `strategy/hint_types.py` unchanged and implements `TextProvider` structurally.

**Evidence:**
- Prompt determinism/allowlist/plain-text: `test_prompt_is_versioned`,
  `test_prompt_is_deterministic_for_identical_request`,
  `test_prompt_contains_only_allowlisted_fields`, `test_prompt_requests_plain_text_not_json`.
- Gatekeeper `llm`-lane-only, deadline preserved:
  `test_client_reached_only_through_llm_lane_execute` (spies on `Gatekeeper.execute`, asserts
  `lane == "llm"` and the exact passed deadline), `test_deadline_is_preserved_not_reset`.
- `ProviderReply` normalization: `test_success_normalizes_to_provider_reply`.
- Typed rejection of bool/negative usage and oversized/empty text:
  `test_malformed_usage_bool_is_rejected`, `test_malformed_usage_negative_is_rejected`,
  `test_empty_output_text_is_rejected`, `test_oversized_output_text_is_rejected` — all raise
  `LlmAdapterError` subclasses that the existing `HintWriter` `except Exception` boundary already
  maps to `FallbackReason.EXCEPTION`.
- Unknown usage never inferred: `test_missing_usage_stays_none_not_inferred`,
  `test_normalize_usage_none_stays_none`.
- Privacy allowlist: `test_privacy_allowlist_disallowed_field_never_reaches_prompt` — asserts no
  cell/verdict/grid/belief/legal-move datum reaches the prompt, and that `HintRenderRequest` has
  no slot for `verdict`/`position`/`destination` at all.
- Zero live network: `test_zero_live_network_uses_fakes_only` — every client is a
  `RecordingClient` fake; no vendor/network import exists in either module.

**Commands run (targeted, before the concurrent T052 worker's files existed in the tree):**
```
uv run pytest tests/unit/infra/test_llm_provider.py tests/contract/test_llm_provider_contract.py -v --no-cov
uv run ruff check src/police_peer/infra/llm_client.py src/police_peer/infra/llm_provider.py tests/unit/infra/test_llm_provider.py tests/contract/test_llm_provider_contract.py
```
Result: 26/26 passed (14 unit + 12 contract). Ruff: all checks passed. Line counts (measured
directly): `llm_client.py` 32, `llm_provider.py` 108, `test_llm_provider.py` 81,
`test_llm_provider_contract.py` 123 — all under the 150-line cap. The full-suite/quality-gate run
is deferred to the Replay-completion-equivalent gate for T049+T052 together, once both land.

**Deviations:** none. `sdk.py`'s concurrent modification in the working tree at review time
belongs to the sibling T052 worker (kit protocol adapter), not this task — confirmed by diff
before staging; this commit touches only the four declared T049 files.

**Follow-on completion:** T013 seals token evidence, T050 supplies the production OpenRouter
transport, and T051 wires the adapter into the runner/composition root on `production-fixes`.
