---
id: T049
status: not_started
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

- [ ] The prompt is versioned and deterministic, built only from allowlisted `HintRenderRequest`
      fields, and requests plain text rather than model-owned JSON semantics.
- [ ] The injected client is called only via `ExternalApiGatekeeper.execute(lane="llm", ...)` with the
      passed deadline.
- [ ] One client response normalizes into `ProviderReply` with provider and model identifiers and
      optional nonnegative token counts.
- [ ] Booleans and negative usage values, and oversized or empty raw text, are rejected with typed
      adapter errors that `HintWriter` maps to a deterministic fallback.
- [ ] Unknown usage stays `None`; token counts are never inferred from the text.
- [ ] Contract tests run fake clients for success, timeout, 429 retry, missing usage, malformed types,
      and the privacy allowlist, and assert zero live network access.

## Verification

- `uv run pytest tests/unit/infra/test_llm_provider.py tests/contract/test_llm_provider_contract.py`
- `uv run ruff check src/police_peer/infra tests`
- `uv run python scripts/check_line_cap.py`

## Result and evidence

(to be filled)
