---
id: T017
status: blocked
priority: P0
task_type: component
component: C06
optional: false
implements:
  - SEC-010
  - REPORT-001
  - REPORT-002
  - REPORT-003
  - REPORT-004
  - REPORT-010
  - REPORT-011
  - REPORT-012
  - REPORT-013
  - QR-008
context_files:
  - docs/components/C06-reporting-league/PRD.md
  - docs/components/C06-reporting-league/PLAN.md
read_set: []
depends_on:
  - T002
  - T003
gates:
  - id: PLANQ-005
    kind: decision
    scope: sender_choice
    blocks: criterion
parallel_safe: true
claimed_by:
claim_expires_at:
write_set:
  - src/police_peer/infra/external_api_gatekeeper.py
  - src/police_peer/reporting/gmail.py
  - tests/unit/infra/test_external_api_gatekeeper.py
  - tests/unit/reporting/test_gmail.py
risk: high
---

# T017 — Implement External-service Gatekeeper And Gmail Adapter

## Expected outcome

A reusable configuration-driven external-service Gatekeeper provides token bucket, queue, DOS lockout, 429 backoff, and optional quota management; the mandatory send-only Gmail adapter is reachable only through it.

## Requirements implemented

- `SEC-010`
- `REPORT-001`
- `REPORT-002`
- `REPORT-003`
- `REPORT-004`
- `REPORT-010`
- `REPORT-011`
- `REPORT-012`
- `REPORT-013`
- `QR-008`

## Relevant context

Tests must never contact Gmail or any optional model provider. Live OAuth authorization and delivery are human-gated, local credential files remain ignored, and any external call introduced by T027 must pass through this boundary without changing Gmail behavior. A draft-only adapter or pretty-printed JSON body is not a counted-report sender and must fail the compliance test.

## Gates

- `PLANQ-005` (`decision`, `blocks: criterion`) — the task may be claimed and implemented now; only the acceptance criterion scoped `sender_choice` waits.

## Constraints

- Do not edit the canonical PRD.
- Do not silently redefine the repository PLAN or task dependencies.
- Do not widen scope or treat a derived design decision as a source requirement.
- Edit only the declared write set; request an orchestrator-approved change before crossing it.
- Escalate requirement conflicts, missing official inputs, and newly discovered work.

## Acceptance criteria

- [ ] OAuth requests only gmail.send and rejects broader granted scopes.
- [ ] The adapter uses the Gmail send operation and cannot silently substitute draft creation or message-body text for the required JSON attachment, per the approved PLANQ-005 sender selection. `{#sender_choice}`
- [ ] All Gmail sends and any later optional model-provider calls pass through the single Gatekeeper; direct service calls are structurally prevented.
- [ ] Token bucket, concurrency, queue, retry/backoff, DOS lockout, and monitoring use approved configuration.
- [ ] credentials.json and token.json are ignored, never logged, and absent from fixtures.
- [ ] 429, quota, expired-token, invalid-recipient, duplicate-send, and network-error paths use test doubles.

## Verification

- `uv run pytest tests/unit/infra/test_external_api_gatekeeper.py tests/unit/reporting/test_gmail.py`
- `uv run ruff check src/police_peer/infra/external_api_gatekeeper.py src/police_peer/reporting/gmail.py tests/unit/infra tests/unit/reporting`
- `uv run python scripts/check_no_secrets.py`

## Implementation plan

To be completed immediately before execution.

## Handoff contract

Report files changed, tests executed, exact test results, decisions made, deviations, blockers, and newly discovered work. Include command output or artifact paths sufficient for the orchestrator to validate every acceptance criterion.

## Result and evidence
