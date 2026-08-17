---
id: T016
status: ready
implementation_state: not_started
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
    scope: official_schema_compliance
    blocks: criterion
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

The official templates have not arrived (OPEN-001, INPUT-001), and no locally defined schema may be presented as one of them. Prose supplies names and broad contents but is not permission to fabricate official attached schemas, consensus-signature bytes, or identifiers.

Development proceeds against the **project artifact contract** recorded under OPEN-001 in `docs/spec/OPEN_QUESTIONS.md`: the four lifecycle artifacts are produced by dedicated builders against a project-defined schema held in `config/official/reporting/`, serialized with the canonical form recorded in `docs/contracts/CT-04-canonical-bytes.md`, and validated by schema, signature, and cross-artifact identifier checks. That contract is sufficient for builders, validators, and their tests; it is not sufficient for counted reporting.

When the official templates arrive they replace the project schema at the same boundary, and the same suite is re-run against them. That replacement is only cheap if the project contract stays *behind* that boundary: no consumer may import the project schema, branch on it, or embed its field names. Consumers read artifacts through the validator and builder interfaces only, so swapping the schema changes one module rather than every caller.

The runtime instances are built during execution: declaration before the series, configuration before each sub-game, log during and finalized after each sub-game, and result after verified settlement. This task defines the contract those builders follow; it does not pre-create completed match data.

## Gates

- `INPUT-001` (`input`, `blocks: criterion`) — the task may be claimed and implemented now against the project artifact contract; only the acceptance criterion scoped `official_schema_compliance` waits for the official templates.

## Constraints

- Do not edit the canonical PRD.
- Do not silently redefine the repository PLAN or task dependencies.
- Do not widen scope or treat a derived design decision as a source requirement.
- Edit only the declared write set; request an orchestrator-approved change before crossing it.
- Escalate requirement conflicts, missing official inputs, and newly discovered work.

## Acceptance criteria

- [ ] Builders, validators, and cross-artifact reconciliation are implemented and tested against the project artifact contract, with committed fixtures for all four lifecycle artifacts.
- [ ] The project artifact contract is reachable only through the builder and validator interfaces. A test asserts that no module outside `src/police_peer/reporting/schemas.py` imports it or hardcodes one of its field names, so an official schema can replace it without touching a consumer.
- [ ] Official template receipt, authority, version, safe hash, and verification status are recorded in the input register without secret contents, and the official schemas replace the project schema at the same boundary with the same suite re-run against them. `{#official_schema_compliance}`
- [ ] Validators distinguish schema failure, signature failure, and cross-artifact identifier mismatch.
- [ ] Per-game config filenames and reported Git commits are deterministic and replayable.
- [ ] Artifact generation contains only schema-supported fields and no private secrets.
- [ ] Builders expose the four approved lifecycle points without creating a declaration/result prematurely or mutating a finalized log.
- [ ] Golden tests are built from the project artifact contract while the official templates are absent, and from sanitized official templates once they arrive. No fixture is labelled official before an official file is registered and verified.
- [ ] Test-only candidate layouts are quarantined from production configuration and used, if retained, only to prove rejection/difference against the official contract.

## Verification

- `uv run pytest tests/contract/report_schemas`
- `uv run ruff check src/police_peer/reporting/schemas.py tests/contract/report_schemas`

## Implementation plan

To be completed immediately before execution.

## Handoff contract

Report files changed, tests executed, exact test results, decisions made, deviations, blockers, and newly discovered work. Include command output or artifact paths sufficient for the orchestrator to validate every acceptance criterion.

## Result and evidence
