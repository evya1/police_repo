---
id: T006
status: done
priority: P0
task_type: component
component: C02
optional: false
implements:
  - STRAT-001
  - STRAT-006
context_files:
  - docs/components/C02-perception-strategy/PRD.md
  - docs/components/C02-perception-strategy/PLAN.md
  - docs/mechanisms/M-02-belief-state.md
read_set: []
depends_on:
  - T005
gates: []
parallel_safe: true
claimed_by: Execution-B
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

- [x] Belief initializes over legal cells and remains normalized after every update.
- [x] Impossible cells and locally known barriers receive no probability.
- [x] Scent and hint evidence updates are deterministic for fixed inputs.
- [x] No API accepts or leaks the opponent's actual position.
- [x] Tests show belief changes can affect downstream move ranking.

## Verification

- `uv run pytest tests/unit/belief`
- `uv run ruff check src/police_peer/belief tests/unit/belief`
- `uv run python scripts/check_line_cap.py src/police_peer/belief tests/unit/belief`

## Implementation plan

1. Implement `BeliefGrid` with uniform legal initialization, query API (`prob`, `most_likely`, `top_k`, `peak_probability`, `as_matrix`), allowed-cell mask tracking, and zero-mass recovery in `_normalize()` that preserves the allowed-cell mask and never leaks probability to excluded/barrier cells.
2. Implement scent observation models (`trust_v1` and `kernel_bayes_v1` via `EmissionProbe` seam).
3. Implement diffusion and half-turn pipeline with fixed update sequence (exclude barrier -> diffuse -> re-exclude barrier -> observe smell -> apply hint -> exclude own cell).
4. Implement landmark registry and deterministic hint parser/updater.
5. Provide comprehensive unit, regression, purity, and property test suites.

## Handoff contract

### Files changed:
- `src/police_peer/belief/__init__.py`: Factory `build_belief`.
- `src/police_peer/belief/grid.py`: `BeliefGrid` class with allowed mask and fail-closed normalization.
- `src/police_peer/belief/hints.py`: Landmark registry, generic fallback, deterministic parser, and updater.
- `src/police_peer/belief/probe.py`: `EmissionProbe` protocol and `kernel_factors`.
- `src/police_peer/belief/update.py`: Pure diffusion, scent observation, and half-turn update order.
- `tests/unit/belief/**`: 77 unit, differential, diffusion, hint, purity, update-order, and normalization property tests.

## Result and evidence

All 77 unit and property tests passing. Zero-mass normalization correctly preserves exclusion masks and deterministically fails when no legal cells remain. Purity verified: no imports of strategy, transport, or opponent objective truth. Ruff and line-cap gates passed.
