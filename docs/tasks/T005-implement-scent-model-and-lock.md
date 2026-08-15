---
id: T005
status: blocked
priority: P0
task_type: component
component: C02
optional: false
implements:
  - STRAT-002
  - STRAT-003
  - STRAT-004
  - STRAT-005
  - CFG-001
  - CFG-004
context_files:
  - docs/components/C02-perception-strategy/PRD.md
  - docs/components/C02-perception-strategy/PLAN.md
  - docs/mechanisms/M-01-scent-model.md
read_set: []
depends_on:
  - T004
gates:
  - id: OPEN-009
    kind: open
    scope: model_lock
    blocks: criterion
parallel_safe: true
claimed_by:
claim_expires_at:
write_set:
  - src/police_peer/scent/model.py
  - src/police_peer/scent/lock.py
  - tests/unit/scent/
  - tests/contract/test_scent_agreement.py
risk: high
---

# T005 — Implement Scent Model And Lock

## Expected outcome

A deterministic 5x5 emission/decay model and pre-series model-lock contract are implemented from an explicitly approved interpretation that resolves OPEN-009.

## Requirements implemented

- `STRAT-002`
- `STRAT-003`
- `STRAT-004`
- `STRAT-005`
- `CFG-001`
- `CFG-004`

## Relevant context

The source fixes center intensity, field size, the multiplicative update recurrence, decay timing, and anti-forgery behavior. It does not state how repeated emission remains within `[0, 0.9]`; T001 must resolve OPEN-009 before this task selects saturation/merge semantics. Clamp/no-clamp, add/max/replace, decay/deposit order, rounding, and transmitted-versus-recomputed variants are differential tests only. No non-authoritative default model overrides that approval.

## Gates

- `OPEN-009` (`open`, `blocks: criterion`) — the task may be claimed and implemented now; only the acceptance criterion scoped `model_lock` waits.

## Constraints

- Do not edit the canonical PRD.
- Do not silently redefine the repository PLAN or task dependencies.
- Do not widen scope or treat a derived design decision as a source requirement.
- Edit only the declared write set; request an orchestrator-approved change before crossing it.
- Escalate requirement conflicts, missing official inputs, and newly discovered work.

## Acceptance criteria

- [ ] Emission at center, edge, and corner is deterministic and bounded to the board.
- [ ] Each full-turn update applies the official recurrence with `rho=0.10`; repeated emission follows the approved OPEN-009 resolution and remains in the approved range.
- [ ] Decay occurs exactly once after both sides act and never produces forged remote scent.
- [ ] Each peer exposes only its own emitted field and consumes only the opponent field.
- [ ] A model document plus numeric examples for new, decaying, and repeatedly emitted cells can be compared and locked before play.
- [ ] Pre-lock tests demonstrate how each unresolved clamp, merge, order, rounding, and transport variant diverges; the approved profile enables exactly one behavior. `{#model_lock}`
- [ ] A mismatch refuses start with a diagnostic and no partial game state.

## Verification

- `uv run pytest tests/unit/scent tests/contract/test_scent_agreement.py`
- `uv run ruff check src/police_peer/scent tests/unit/scent tests/contract/test_scent_agreement.py`

## Implementation plan

To be completed immediately before execution.

## Handoff contract

Report files changed, tests executed, exact test results, decisions made, deviations, blockers, and newly discovered work. Include command output or artifact paths sufficient for the orchestrator to validate every acceptance criterion.

## Result and evidence
