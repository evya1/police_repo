---
id: T043-extend-kpi-harness
status: done
priority: P0
task_type: governance
component: C02
optional: false
context_files:
  - docs/TODO_police_strategy.md
  - docs/PLAN_police_strategy.md
  - docs/PRD_police_strategy.md
read_set: []
depends_on:
  - PS-01
gates: []
parallel_safe: true
claimed_by: ORC
claim_expires_at:
write_set:
  - tests/integration/test_strategy_selfplay_kpi.py
risk: low
---

# T043-extend-kpi-harness — Write-set extension: KPI self-play harness

## Purpose

Record the approved write-set extension to `tests/integration/test_strategy_selfplay_kpi.py`
for the Stage-3 KPI harness so that PS-06 can run the self-play + property +
determinism + perf suites without silently widening T007's or T021's declared scope.

## Extension

T007's declared write set is `src/police_peer/strategy/` + `tests/unit/strategy/`.
T021 absorbs the property-suite + coverage close-out (`tests/property/`). The KPI
self-play harness lives in `tests/integration/` and is needed by PS-06 (KPI
self-play + property + determinism + perf + coverage close-out).

**Decision:** extend T007's write set to include
`tests/integration/test_strategy_selfplay_kpi.py` for the KPI harness classes and
fixtures only. PS-06 owns the harness usage; PS-06 also owns the property suite in
`tests/property/` (absorbed by T021). No other integration test files are added by
this extension.

## Evidence

- Recorded in `docs/tasks/T043-extend-kpi-harness.md` before any strategy task is
  claimed (workflow §4: no silent scope expansion).
- ORC-verified: the path `tests/integration/test_strategy_selfplay_kpi.py` does not
  yet exist on the `police-strategy` branch (`7ce031d`); it will be created by PS-06
  (or PS-02/PS-03 as harness scaffolding) per this approved extension.
- Mirrors the thief-repo pattern: `thief_repo` recorded the same extension as part of
  T007's result evidence (`src/thief_peer/wire/__init__.py` extended,
  `tests/integration/test_strategy_selfplay_kpi.py` created).
