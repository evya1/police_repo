---
id: T016
status: blocked
priority: P0
task_type: component
component: C06
optional: false
implements:
  - CFG-009
  - CFG-010
  - REPORT-005
  - REPORT-006
  - REPORT-007
  - REPORT-008
  - REPORT-009
context_files:
  - docs/components/C06-reporting-league/PRD.md
  - docs/components/C06-reporting-league/PLAN.md
read_set: []
depends_on: []
gates:
  - id: INPUT-001
    kind: input
    scope: schema_adoption
    blocks: start
parallel_safe: true
claimed_by:
claim_expires_at:
write_set:
  - src/police_peer/reporting/schemas.py
  - config/official/reporting/
  - tests/contract/report_schemas/
risk: high
---

# T016 — Adopt Official Report Artifact Schemas

## Expected outcome

The four official JSON schemas/templates are adopted without alteration, with validators, lifecycle-aware builders, and exact filename/common-identifier rules.

## Requirements implemented

- `CFG-009`
- `CFG-010`
- `REPORT-005`
- `REPORT-006`
- `REPORT-007`
- `REPORT-008`
- `REPORT-009`

## Relevant context

OPEN-001 and OPEN-007 are hard blockers. Prose supplies names and broad contents but is not permission to fabricate official attached schemas, consensus-signature bytes, or identifiers. Conflicting flat/nested layouts and differing declaration/log/result fields demonstrate why no auxiliary artifact generator/schema may be relabeled as official.

The runtime instances are built during execution: declaration before the series, configuration before each sub-game, log during/finalized after each sub-game, and result after verified settlement. This task adopts the official contract those builders must follow; it does not pre-create completed match data.

## Gates

- `INPUT-001` (`input`, `blocks: start`) — this task cannot be claimed until the gate resolves.

## Constraints

- Do not edit the canonical PRD.
- Do not silently redefine the repository PLAN or task dependencies.
- Do not widen scope or treat a derived design decision as a source requirement.
- Edit only the declared write set; request an orchestrator-approved change before crossing it.
- Escalate requirement conflicts, missing official inputs, and newly discovered work.

## Acceptance criteria

- [ ] Official template receipt, authority, version, safe hash, and verification status are recorded in the input register without secret contents.
- [ ] Validators distinguish schema failure, signature failure, and cross-artifact identifier mismatch.
- [ ] Per-game config filenames and reported Git commits are deterministic and replayable.
- [ ] Artifact generation contains only schema-supported fields and no private secrets.
- [ ] Builders expose the four approved lifecycle points without creating a declaration/result prematurely or mutating a finalized log.
- [ ] Golden tests are built from sanitized official templates, not invented examples.
- [ ] Test-only candidate layouts are quarantined from production configuration and used, if retained, only to prove rejection/difference against the official contract.

## Verification

- `uv run pytest tests/contract/report_schemas`
- `uv run ruff check src/police_peer/reporting/schemas.py tests/contract/report_schemas`

## Implementation plan

To be completed immediately before execution.

## Handoff contract

Report files changed, tests executed, exact test results, decisions made, deviations, blockers, and newly discovered work. Include command output or artifact paths sufficient for the orchestrator to validate every acceptance criterion.

## Result and evidence
