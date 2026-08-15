---
id: T006
status: blocked
priority: P0
implements:
  - STRAT-001
  - STRAT-006
depends_on:
  - T005
parallel_safe: true
claimed_by:
claim_expires_at:
write_set:
  - src/police_peer/belief/
  - tests/unit/belief/
risk: medium
---

# T006 — Implement Belief State

## Expected outcome

The role maintains a normalized belief distribution updated from opponent scent and natural-language hint evidence, without learning hidden truth.

## Requirements implemented

- `STRAT-001`
- `STRAT-006`

## Relevant context

Belief is local inference, never objective opponent state. Strategy and GUI consume snapshots through narrow interfaces.

## Constraints

- Do not edit the canonical PRD.
- Do not silently redefine the repository PLAN or task dependencies.
- Do not widen scope or treat a derived design decision as a source requirement.
- Edit only the declared write set; request an orchestrator-approved change before crossing it.
- Escalate requirement conflicts, missing official inputs, and newly discovered work.

## Acceptance criteria

- [ ] Belief initializes over legal cells and remains normalized after every update.
- [ ] Impossible cells and locally known barriers receive no probability.
- [ ] Scent and hint evidence updates are deterministic for fixed inputs.
- [ ] No API accepts or leaks the opponent's actual position.
- [ ] Tests show belief changes can affect downstream move ranking.

## Verification

- `uv run pytest tests/unit/belief`
- `uv run ruff check src/police_peer/belief tests/unit/belief`

## Implementation plan

To be completed immediately before execution.

## Handoff contract

Report files changed, tests executed, exact test results, decisions made, deviations, blockers, and newly discovered work. Include command output or artifact paths sufficient for the orchestrator to validate every acceptance criterion.

## Result and evidence
