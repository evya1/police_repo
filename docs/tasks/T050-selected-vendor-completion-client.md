---
id: T050
status: done
priority: P2
task_type: component
component: C06
optional: true
implements:
  - STRAT-008
  - SEC-010
  - QR-014
context_files:
  - docs/components/C06-reporting-league/PRD.md
  - docs/components/C06-reporting-league/PLAN.md
  - docs/PRD_llm_provider.md
  - docs/PLAN_llm_provider.md
read_set: []
depends_on:
  - T049
gates:
  - id: PLANQ-003
    kind: decision
    scope: provider_choice
    blocks: start
parallel_safe: true
claimed_by:
claim_expires_at:
write_set:
  - pyproject.toml
  - uv.lock
  - src/police_peer/infra/selected_vendor_client.py
  - tests/contract/test_selected_vendor_client.py
  - docs/evidence/llm-provider/
risk: high
---

# T050 — Selected vendor CompletionClient (gated)

## Expected outcome

One `CompletionClient` implementation for the approved vendor, added together with its optional
dependency and lock entry, with typed timeout and rate-error mapping and fake-transport tests.

## Requirements implemented

- `STRAT-008`
- `SEC-010`
- `QR-014`

## Relevant context

PLANQ-003 selected the optional OpenRouter transport while retaining deterministic template mode as
the default legal path. The approved production profile is recorded in the Result section and in
`config/private/llm-openrouter.toml`; the implementation is `infra/openrouter_client.py`.

## Gates

- `PLANQ-003` is resolved: OpenRouter with the dependency-free standard-library HTTP transport,
  explicit model/provider routing, environment-only credential, token/deadline/rate bounds, fake
  contract transport in CI, and separately authorized opt-in live evidence.

## Constraints

- Edit only the declared write set.
- Never read secrets outside the composition root; never log prompts, raw secrets, or private headers.
- Tests mock or fake the SDK transport and never call the live service. A separate opt-in smoke
  command may create sanitized evidence only when explicitly authorized.
- Record the lock diff and the dependency license and security checks.
- Every code and test file stays below 150 logical lines.

## Acceptance criteria

- [x] The approved SDK, model, environment variable names, rates, and budget are recorded before any
      code is written.
- [x] Only the selected optional dependency is added; the lock shows no unrelated drift.
- [x] The client uses the selected SDK's typed timeout and rate errors and passes an explicit timeout
      and token cap.
- [x] Contract tests use a fake transport; CI performs no live provider call and requires no key.
- [x] `scripts/check_no_secrets.py` passes and no credential appears in code, logs, fixtures,
      exceptions, or artifacts.

## Verification

- `uv lock --check`
- `uv sync --locked --all-groups`
- `uv run pytest tests/contract/test_selected_vendor_client.py`
- `uv run ruff check .`
- `uv run python scripts/check_no_secrets.py`

## Result and evidence

Completed on `production-fixes` with the approved dependency-free standard-library HTTP transport:
`infra/openrouter_client.py`. OpenRouter uses `OPENROUTER_API_KEY`, optional
`OPENROUTER_BASE_URL`, model `inclusionai/ling-3.0-flash` pinned to provider slug `novita`, a
30-second step deadline, 10 output tokens per call, one call per eligible step, and the shared
Gatekeeper's 30-request-per-minute default. Contract tests inject an in-memory opener and cover
success, routing, usage, authentication, 429, timeout, connection, malformed response, deadline,
and token-cap behavior; normal tests and CI never make a live provider call.
