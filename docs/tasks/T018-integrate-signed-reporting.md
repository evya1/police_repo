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

`artifacts.py` builds/signs the four artifacts from CT-06 and enforces
immutability of a finalized log; `pipeline.py` orchestrates settle → M-07
reconcile → build → one Gatekeeper send. OPEN-004's sanction criterion waits;
implement the conservative unsettled state only. Idempotency: persist the
per-`game_id` result-hash sent guard before send. Exact attachment bytes
asserted against a fake send. Dependency requests: none beyond T016/T017
outputs.

(Reviewed 2026-08-18: analyzed by deepseek-v4-pro, approved by glm-5.2; full rationale in docs/evidence/c06-prep-01/analysis.md sections 2, 3, 5.)

## Behavioral test plan

(gate note: `OPEN-004 blocks: criterion` on `sanction_settlement` — implement the conservative guard only)
- **unit** — artifact totals derive strictly from CT-06 records + the fixed GAME-013 table; the idempotent sent-state guard refuses a second send for the same `game_id`.
- **boundary-adapter** — the exact MIME attachment bytes passed to a mock are asserted byte-for-byte; exactly one send per settled series.
- **integration** — declaration → per-sub-game configuration → finalized log → result is produced in lifecycle order, then exactly one send fires.
- **failure** — missing, incomplete, or conflicting required reports reach the explicit unsettled state with preserved evidence (M-07); tampered/schema-invalid records are refused.
- **security** — signature verification precedes any send; no plaintext report is ever accepted.
- **determinism** — with seeded verified records and injected timestamp/commit values, artifact bytes are identical across runs.

## Handoff contract

Report files changed, tests executed, exact test results, decisions made, deviations, blockers, and newly discovered work. Include command output or artifact paths sufficient for the orchestrator to validate every acceptance criterion.

## Result and evidence
