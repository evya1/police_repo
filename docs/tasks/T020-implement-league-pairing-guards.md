---
id: T020
status: blocked
priority: P0
task_type: component
component: C06
optional: false
implements:
  - LEAGUE-002
  - LEAGUE-003
  - LEAGUE-004
  - LEAGUE-007
context_files:
  - docs/components/C06-reporting-league/PRD.md
  - docs/components/C06-reporting-league/PLAN.md
read_set: []
depends_on:
  - T018
  - T019
gates:
  - id: G-LIVE
    kind: input_gate
    scope: pairing_preflight
    blocks: criterion
parallel_safe: true
claimed_by:
claim_expires_at:
write_set:
  - src/police_peer/league/preflight.py
  - tests/unit/league/test_pairing_guards.py
  - tests/integration/test_preflight.py
risk: high
---

# T020 — Implement League Pairing Guards

## Expected outcome

Preflight guards enforce counted-match eligibility and truthful declarations, while preserving auditable evidence for computational fairness.

## Requirements implemented

- `LEAGUE-002`
- `LEAGUE-003`
- `LEAGUE-004`
- `LEAGUE-007`

## Relevant context

The system reports required inputs but never invents lecturer-side normalization. Warm-ups remain explicitly non-counted.

## Gates

- `G-LIVE` (`input_gate`, `blocks: criterion`) — the task may be claimed and implemented now; only the acceptance criterion scoped `pairing_preflight` waits.

## Constraints

- Do not edit the canonical PRD.
- Do not silently redefine the repository PLAN or task dependencies.
- Do not widen scope or treat a derived design decision as a source requirement.
- Edit only the declared write set; request an orchestrator-approved change before crossing it.
- Escalate requirement conflicts, missing official inputs, and newly discovered work.

## Acceptance criteria

- [ ] The peer refuses an eleventh counted match or a second counted match with the same opponent.
- [ ] At least two distinct opponents is tracked as a submission obligation, not faked before completion.
- [ ] Prior counted-match declarations are signed, compared, and retained.
- [ ] Warm-up and counted modes are unambiguous and cannot share report state accidentally.
- [ ] Hardware/code/token evidence is complete but contains no local fairness score formula.
- [ ] Preflight eligibility, declaration, and endpoint checks pass against real opponent/endpoint data once `G-LIVE` is satisfied. `{#pairing_preflight}`

## Verification

- `uv run pytest tests/unit/league/test_pairing_guards.py tests/integration/test_preflight.py`
- `uv run ruff check src/police_peer/league/preflight.py tests/unit/league/test_pairing_guards.py tests/integration/test_preflight.py`

## Implementation plan

To be completed immediately before execution.

## Handoff contract

Report files changed, tests executed, exact test results, decisions made, deviations, blockers, and newly discovered work. Include command output or artifact paths sufficient for the orchestrator to validate every acceptance criterion.

## Result and evidence
