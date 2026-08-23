---
id: T050
status: blocked
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

This task carries the start-blocking provider decision that previously sat on T027. It cannot be
claimed until `PLANQ-003` is resolved **in writing**.

`PLANQ-003` is currently **PARTIALLY RESOLVED**: deterministic template mode with no external
provider is sufficient for the core MVP and must remain a fully legal way to play a complete game.
Whether to enable a provider at all, and the specific provider, model, cadence, budget, and rate
limits, remain `TBD_TEAM_DECISION`.

The module name `selected_vendor_client.py` is a placeholder. It is renamed to the approved vendor's
name by the orchestrator at the same time the gate is resolved, never by a worker.

## Gates

- `PLANQ-003` (`decision`, `blocks: start`) — this task cannot be claimed until provider, exact
  SDK and version policy, model identifier, approved secret environment variable, token budget,
  timeout, retry/rate limits, and live-evidence policy are all recorded.

## Constraints

- Edit only the declared write set.
- Never read secrets outside the composition root; never log prompts, raw secrets, or private headers.
- Tests mock or fake the SDK transport and never call the live service. A separate opt-in smoke
  command may create sanitized evidence only when explicitly authorized.
- Record the lock diff and the dependency license and security checks.
- Every code and test file stays below 150 logical lines.

## Acceptance criteria

- [ ] The approved SDK, model, environment variable names, rates, and budget are recorded before any
      code is written.
- [ ] Only the selected optional dependency is added; the lock shows no unrelated drift.
- [ ] The client uses the selected SDK's typed timeout and rate errors and passes an explicit timeout
      and token cap.
- [ ] Contract tests use a fake transport; CI performs no live provider call and requires no key.
- [ ] `scripts/check_no_secrets.py` passes and no credential appears in code, logs, fixtures,
      exceptions, or artifacts.

## Verification

- `uv lock --check`
- `uv sync --locked --all-groups`
- `uv run pytest tests/contract/test_selected_vendor_client.py`
- `uv run ruff check .`
- `uv run python scripts/check_no_secrets.py`

## Result and evidence

BLOCKED — `PLANQ-003` is not resolved. No dependency, vendor module, or SDK import may be added.
