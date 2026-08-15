---
id: T001
status: ready
priority: P0
task_type: governance
component: system
optional: false
implements:
  - CFG-001
  - CFG-004
  - CFG-005
  - REPORT-006
  - REPORT-009
  - SUB-009
  - SUB-010
context_files:
  - docs/PRD.md
  - docs/PLAN.md
read_set: []
depends_on: []
gates:
  - id: G-OFFICIAL
    kind: input_gate
    scope: official_schemas
    blocks: criterion
  - id: G-TEAM
    kind: input_gate
    scope: team_metadata
    blocks: criterion
  - id: G-LIVE
    kind: input_gate
    scope: live_endpoints
    blocks: criterion
  - id: G-OFFICIAL
    kind: input_gate
    scope: sanction_minimum_decisions
    blocks: criterion
  - id: G-OFFICIAL
    kind: input_gate
    scope: serialization_series_scent
    blocks: criterion
  - id: G-OFFICIAL
    kind: input_gate
    scope: match_profile_lock
    blocks: criterion
parallel_safe: true
claimed_by:
claim_expires_at:
write_set:
  - config/official/
  - docs/inputs/INPUT_REGISTER.md
  - docs/spec/OPEN_QUESTIONS.md
risk: high
---

# T001 — Resolve Official Inputs And Match Profile

## Expected outcome

A human-approved input packet closes or explicitly defers every blocking official-input and cross-team agreement question without inventing a schema, identifier, or sanction.

## Requirements implemented

- `CFG-001`
- `CFG-004`
- `CFG-005`
- `REPORT-006`
- `REPORT-009`
- `SUB-009`
- `SUB-010`

## Relevant context

This task coordinates intake across OPEN-001 through OPEN-011; it is claimable and begins requesting/registering inputs immediately — no `depends_on` task and no `gates:` entry blocks its start. Team name `ZeroOne`, team number `01`, and GitHub handles `evya1` and `Us5rName` are recorded non-secret inputs. The orchestrator obtains the remaining official attachments, authoritative clarifications, eight-character final-project group code, repository/endpoint values, and any private form-only values, then registers and verifies each input without storing secret contents. Each unresolved item is represented below as a criterion-scoped gate on the specific acceptance criterion it affects, not as a whole-task blocker.

## Gates

- `G-OFFICIAL` (`input_gate`, `blocks: criterion`) — the task may be claimed and implemented now; only the acceptance criterion scoped `official_schemas` waits.
- `G-TEAM` (`input_gate`, `blocks: criterion`) — the task may be claimed and implemented now; only the acceptance criterion scoped `team_metadata` waits.
- `G-LIVE` (`input_gate`, `blocks: criterion`) — the task may be claimed and implemented now; only the acceptance criterion scoped `live_endpoints` waits.
- `G-OFFICIAL` (`input_gate`, `blocks: criterion`) — the task may be claimed and implemented now; only the acceptance criterion scoped `sanction_minimum_decisions` waits.
- `G-OFFICIAL` (`input_gate`, `blocks: criterion`) — the task may be claimed and implemented now; only the acceptance criterion scoped `serialization_series_scent` waits.
- `G-OFFICIAL` (`input_gate`, `blocks: criterion`) — the task may be claimed and implemented now; only the acceptance criterion scoped `match_profile_lock` waits.

## Constraints

- Do not edit the canonical PRD.
- Do not silently redefine the repository PLAN or task dependencies.
- Do not widen scope or treat a derived design decision as a source requirement.
- Edit only the declared write set; request an orchestrator-approved change before crossing it.
- Escalate requirement conflicts, missing official inputs, and newly discovered work.

## Acceptance criteria

- [ ] The four official reporting templates/schemas and official Moodle form are either attached verbatim or still marked MISSING OFFICIAL INPUT; completed runtime match instances and conflicting flat/nested candidate layouts are not mistaken for the missing schema contract. `{#official_schemas}`
- [ ] The confirmed team name, number, and GitHub handles are retained, while the valid eight-character group code and role ownership are resolved without committing private data. `{#team_metadata}` The sibling URL, public MCP address, and opponent agreement values are resolved once a live opponent/endpoint is available. `{#live_endpoints}`
- [ ] OPEN-004 and OPEN-005 have written lecturer/team decisions; no sanction or Minimum direction is inferred. `{#sanction_minimum_decisions}`
- [ ] OPEN-007, OPEN-008, and OPEN-009 are resolved or explicitly deferred; compact/spaced serialization, Nonce placement, role schedule, tie aggregation, and scent clamp/merge/update behavior remain test-only branches until approved. `{#serialization_series_scent}`
- [ ] The agreed match profile identifies version, axes, starts, numeric terms, scent model with repeated-emission example, and integrity envelope at the level actually approved. `{#match_profile_lock}`
- [ ] Each arriving input is recorded in `docs/inputs/INPUT_REGISTER.md`, verified, and reflected in affected OPEN items; a receipt that does not change approved normative meaning does not create a Change Request.
- [ ] Any material change to an approved canonical product requirement or PRD contract has an approved Change Request naming affected IDs, source/authority, impact, approval, and resulting PRD version before downstream reconciliation.
- [ ] A durable technical choice uses an ADR only when warranted, and newly discovered implementation work receives a new stable task ID.

## Verification

- `uv run python scripts/run_quality_gates.py`
- `uv run ruff check .`

## Implementation plan

To be completed immediately before execution.

## Handoff contract

Report files changed, tests executed, exact test results, decisions made, deviations, blockers, and newly discovered work. Include command output or artifact paths sufficient for the orchestrator to validate every acceptance criterion.

## Result and evidence
