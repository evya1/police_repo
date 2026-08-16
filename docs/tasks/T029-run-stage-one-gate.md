---
id: T029
status: blocked
implementation_state: not_started
priority: P1
task_type: verification
component: C01
optional: false
implements:
  - GAME-013
  - GAME-014
context_files:
  - docs/components/C01-game-core/PRD.md
  - docs/components/C01-game-core/PLAN.md
read_set: []
depends_on:
  - T004
  - T028
gates:
  - id: OPEN-011
    kind: open
    scope: cap_refusal
    blocks: criterion
parallel_safe: true
claimed_by:
claim_expires_at:
write_set:
  - tests/integration/test_local_two_agent_game.py
  - docs/evidence/stage1-gate.md
risk: medium
---

# T029 — Run The Stage-1 Domain Gate

## Expected outcome

A local, single-process, two-agent scripted run exercises `T004`'s domain module end-to-end against `T028`'s example contract to a terminal outcome, with recorded determinism evidence, before any transport/strategy work builds on the domain layer.

## Requirements implemented

- `GAME-013`
- `GAME-014`

## Relevant context

This is a test-only harness, not the live orchestrator: it drives both agents' turns through this repository's own domain module (which already models full board/turn/capture logic from locally available state) in one process. It does not import the sibling repository and does not stand in for `ARCH-002`'s two-separate-processes requirement, which applies to the shipped peers from `T009`/`T010` onward. `GAME-014`'s move-cap-versus-survival-threshold relationship remains blocked by `OPEN-011`; this gate exercises the survival-threshold path, which is unambiguous, and asserts (rather than guesses) that the move-cap path is refused pending resolution.

## Gates

- `OPEN-011` (`open`, `blocks: criterion`) — the task may be claimed and implemented now; only the acceptance criterion scoped `cap_refusal` waits.

## Constraints

- Do not edit the canonical PRD.
- Do not silently redefine the repository PLAN or task dependencies.
- Do not import or reference the sibling repository; the harness uses only this repository's own domain module.
- Edit only the declared write set; request an orchestrator-approved change before crossing it.
- Escalate requirement conflicts, missing official inputs, and newly discovered work.

## Acceptance criteria

- [ ] A scripted run of legal moves reaches a `CAPTURE` outcome with scores exactly 20/5.
- [ ] A scripted run of legal moves reaches a `SURVIVAL` outcome at the configured `survival_threshold` with scores exactly 5/10.
- [ ] A move beyond the barrier quota is rejected within the same run without corrupting prior state.
- [ ] Two independent runs with identical `(config, action sequence)` produce byte-identical legal-move ordering, outcome, and scores.
- [ ] A run that reaches `max_moves` without reaching `survival_threshold` or a capture does not silently report an outcome; it fails loudly citing `OPEN-011`. `{#cap_refusal}`
- [ ] `docs/evidence/stage1-gate.md` records the exact commands run and their results, not a narrative claim.

## Verification

- `uv run pytest tests/integration/test_local_two_agent_game.py`
- `uv run python scripts/run_quality_gates.py`

## Implementation plan

To be completed immediately before execution.

## Handoff contract

Report files changed, tests executed, exact test results, decisions made, deviations, blockers, and newly discovered work. Include command output or artifact paths sufficient for the orchestrator to validate every acceptance criterion.

## Result and evidence
