---
id: T018
status: blocked
priority: P0
task_type: integration
component: C06
optional: false
implements:
  - REPORT-001
  - REPORT-004
  - REPORT-005
  - REPORT-006
  - REPORT-007
  - REPORT-008
  - REPORT-009
context_files:
  - docs/components/C06-reporting-league/PRD.md
  - docs/components/C06-reporting-league/PLAN.md
  - docs/mechanisms/M-07-report-reconciliation.md
  - docs/contracts/CT-06-verified-result.md
read_set: []
depends_on:
  - T012
  - T013
  - T015
  - T016
  - T017
gates:
  - id: OPEN-004
    kind: open
    scope: sanction_settlement
    blocks: criterion
parallel_safe: false
claimed_by:
claim_expires_at:
write_set:
  - src/police_peer/reporting/pipeline.py
  - src/police_peer/reporting/artifacts.py
  - tests/integration/test_reporting_pipeline.py
risk: high
---

# T018 — Integrate Signed Reporting

## Expected outcome

A settled legal series produces mutually consistent, signed JSON artifacts and triggers exactly one independent automated report through the Gatekeeper.

## Requirements implemented

- `REPORT-001`
- `REPORT-004`
- `REPORT-005`
- `REPORT-006`
- `REPORT-007`
- `REPORT-008`
- `REPORT-009`

## Relevant context

The unresolved missing/conflicting-report sanction must follow the approved OPEN-004 resolution. Plaintext and partially settled reports are invalid.

Artifact instances are produced in lifecycle order: one declaration before the series, one locked configuration and one incrementally recorded/finalized log per sub-game, and one result only after verified settlement. T016 must first supply the official schema/canonical contract.

## Gates

- `OPEN-004` (`open`, `blocks: criterion`) — the task may be claimed and implemented now; only the acceptance criterion scoped `sanction_settlement` waits.

## Constraints

- Do not edit the canonical PRD.
- Do not silently redefine the repository PLAN or task dependencies.
- Do not widen scope or treat a derived design decision as a source requirement.
- Edit only the declared write set; request an orchestrator-approved change before crossing it.
- Escalate requirement conflicts, missing official inputs, and newly discovered work.

## Acceptance criteria

- [ ] Artifact totals are derived from verified sub-game records and the fixed scoring table.
- [ ] Declaration, configuration, log, and result instances are created only at their approved lifecycle points; finalized evidence is immutable.
- [ ] Common identifiers, repositories, commits, hardware/model, token totals, and timestamps reconcile across all four artifact families.
- [ ] The sender is idempotent and cannot silently send a second counted report.
- [ ] An unsettled, tampered, schema-invalid, or peer-inconsistent result follows the approved refusal/sanction path once OPEN-004 resolves. `{#sanction_settlement}`
- [ ] Integration tests assert the exact attachment bytes passed to a mock Gmail service.

## Verification

- `uv run pytest tests/integration/test_reporting_pipeline.py`
- `uv run ruff check src/police_peer/reporting tests/integration/test_reporting_pipeline.py`

## Implementation plan

To be completed immediately before execution.

## Handoff contract

Report files changed, tests executed, exact test results, decisions made, deviations, blockers, and newly discovered work. Include command output or artifact paths sufficient for the orchestrator to validate every acceptance criterion.

## Result and evidence
