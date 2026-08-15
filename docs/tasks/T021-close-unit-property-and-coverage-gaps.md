---
id: T021
status: blocked
priority: P1
task_type: verification
component: system
optional: false
implements:
  - QR-005
  - QR-009
  - QR-010
  - QR-011
context_files:
  - docs/PRD.md
  - docs/PLAN.md
read_set: []
depends_on:
  - T004
  - T005
  - T006
  - T007
  - T008
gates: []
parallel_safe: true
claimed_by:
claim_expires_at:
write_set:
  - tests/property/
  - tests/coverage_exceptions.md
risk: medium
---

# T021 — Close Unit Property And Coverage Gaps

## Expected outcome

Cross-cutting property tests and coverage review close critical rule/integrity gaps while preserving the 150-line and Ruff-zero thresholds.

## Requirements implemented

- `QR-005`
- `QR-009`
- `QR-010`
- `QR-011`

## Relevant context

Component tasks own their public-API tests. This task adds boundary/property cases and measures gaps; it does not postpone all testing until the end.

## Constraints

- Do not edit the canonical PRD.
- Do not silently redefine the repository PLAN or task dependencies.
- Do not widen scope or treat a derived design decision as a source requirement.
- Edit only the declared write set; request an orchestrator-approved change before crossing it.
- Escalate requirement conflicts, missing official inputs, and newly discovered work.

## Acceptance criteria

- [ ] Every public API has happy and error-path tests with external services replaced by doubles.
- [ ] Board, scent, belief normalization, scoring, and hash invariants have property-style coverage.
- [ ] Global coverage is at least 85%, with critical integrity/rules paths higher and no blanket omit rules.
- [ ] Ruff reports zero violations and every code file satisfies the configured 150-line metric.
- [ ] Expected results for non-obvious edge cases are documented in tests.

## Verification

- `uv run pytest`
- `uv run ruff check .`
- `uv run python scripts/check_line_cap.py`

## Implementation plan

To be completed immediately before execution.

## Handoff contract

Report files changed, tests executed, exact test results, decisions made, deviations, blockers, and newly discovered work. Include command output or artifact paths sufficient for the orchestrator to validate every acceptance criterion.

## Result and evidence
