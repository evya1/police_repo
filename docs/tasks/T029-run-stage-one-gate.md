---
id: T029
status: done
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
gates: []
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

This test harness drives both agents' turns through this repository's domain module in one process
without importing the sibling repository. The shipped peers satisfy ARCH-002 through the separate
T009/T010 production processes. GAME-014 uses the conservative survival-threshold profile and
fails closed on an incompatible move-cap configuration.

## Gates

- None. The production termination contract and failure path are verified.

## Constraints

- Do not edit the canonical PRD.
- Do not silently redefine the repository PLAN or task dependencies.
- Do not import or reference the sibling repository; the harness uses only this repository's own domain module.
- Edit only the declared write set; request an orchestrator-approved change before crossing it.
- Escalate requirement conflicts, missing official inputs, and newly discovered work.

## Acceptance criteria

- [x] A scripted run of legal moves reaches a `CAPTURE` outcome with scores exactly 20/5.
- [x] A scripted run of legal moves reaches a `SURVIVAL` outcome at the configured `survival_threshold` with scores exactly 5/10.
- [x] A move beyond the barrier quota is rejected within the same run without corrupting prior state.
- [x] Two independent runs with identical `(config, action sequence)` produce byte-identical legal-move ordering, outcome, and scores.
- [x] An incompatible move-cap/survival contract fails closed before play. `{#cap_refusal}`
- [x] `docs/evidence/stage1-gate.md` records the exact commands and successful results.

## Verification

- `uv run pytest tests/integration/test_local_two_agent_game.py`
- `uv run python scripts/run_quality_gates.py`

## Implementation plan

To be completed immediately before execution.

## Handoff contract

Report files changed, tests executed, exact test results, decisions made, deviations, blockers, and newly discovered work. Include command output or artifact paths sufficient for the orchestrator to validate every acceptance criterion.

## Result and evidence

Complete. `docs/evidence/stage1-gate.md` records the deterministic capture, survival,
precedence, and incompatible-contract checks.
