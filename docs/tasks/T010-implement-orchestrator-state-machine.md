---
id: T010
status: blocked
priority: P0
task_type: integration
component: C04
optional: false
implements:
  - ARCH-004
  - ARCH-005
  - ARCH-006
context_files:
  - docs/components/C04-runtime-reliability/PRD.md
  - docs/components/C04-runtime-reliability/PLAN.md
  - docs/contracts/CT-01-game-state.md
  - docs/contracts/CT-02-strategy-decision.md
  - docs/contracts/CT-03-peer-wire.md
read_set: []
depends_on:
  - T004
  - T005
  - T008
  - T009
gates: []
parallel_safe: true
claimed_by:
claim_expires_at:
write_set:
  - src/police_peer/orchestration/
  - tests/unit/orchestration/
risk: high
---

# T010 — Implement Orchestrator State Machine

## Expected outcome

A thin Orchestrator drives one explicit lifecycle state machine, delegates decisions and I/O, and rejects all unlisted transitions.

## Requirements implemented

- `ARCH-004`
- `ARCH-005`
- `ARCH-006`

## Relevant context

The Orchestrator is the only subsystem gateway but must not absorb strategy, domain, transport, integrity, or reporting logic.

## Constraints

- Do not edit the canonical PRD.
- Do not silently redefine the repository PLAN or task dependencies.
- Do not widen scope or treat a derived design decision as a source requirement.
- Edit only the declared write set; request an orchestrator-approved change before crossing it.
- Escalate requirement conflicts, missing official inputs, and newly discovered work.

## Acceptance criteria

- [ ] The legal transition map covers negotiation, ready, move, commit, acknowledge, wait, reveal, audit, report, terminal, and failure states.
- [ ] Every unlisted transition raises a typed error and leaves state unchanged.
- [ ] Side effects are invoked through interfaces and can be replaced with test doubles.
- [ ] Restart inputs can reconstruct the last persisted safe state without opponent truth.
- [ ] Happy, timeout, tamper, capture, survival, and shutdown paths are tested.

## Verification

- `uv run pytest tests/unit/orchestration`
- `uv run ruff check src/police_peer/orchestration tests/unit/orchestration`

## Implementation plan

To be completed immediately before execution.

## Handoff contract

Report files changed, tests executed, exact test results, decisions made, deviations, blockers, and newly discovered work. Include command output or artifact paths sufficient for the orchestrator to validate every acceptance criterion.

## Result and evidence
