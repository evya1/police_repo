---
id: T042-extend-wire-brain-swap
status: done
priority: P0
task_type: governance
component: C02
optional: false
context_files:
  - docs/TODO_police_strategy.md
  - docs/PLAN_police_strategy.md
  - src/police_peer/wire/__init__.py
read_set: []
depends_on:
  - PS-01
gates: []
parallel_safe: true
claimed_by: ORC
claim_expires_at:
write_set:
  - src/police_peer/wire/__init__.py
risk: low
---

# T042-extend-wire-brain-swap — Write-set extension: S3 BrainDrivenEngine seam

## Purpose

Record the approved write-set extension to `src/police_peer/wire/__init__.py` for the
Stage-3 brain-swap seam (`BrainDrivenEngine`) so that PS-02/PS-03/PS-04 can wire the real
`PoliceBrain` without silently widening T007's declared scope.

## Extension

T007's declared write set is `src/police_peer/strategy/` + `tests/unit/strategy/`.
The S3 glue swap requires `src/police_peer/wire/__init__.py` (the existing
`StandInEngine` is subclassed by `BrainDrivenEngine` in the same file). This file is
owned by the stage-2 glue, not by T007's strategy write set.

**Decision:** extend T007's write set to include `src/police_peer/wire/__init__.py`
for the `BrainDrivenEngine` addition only. No other edits to this file are permitted
by the strategy stage; the stage-2 glue contract (`TurnEngine` seam) is immutable
modulo the `BrainDrivenEngine` subclass.

## Evidence

- Recorded in `docs/tasks/T042-extend-wire-brain-swap.md` before any strategy task is
  claimed (workflow §4: no silent scope expansion).
- ORC-verified: `src/police_peer/wire/__init__.py` exists on the `police-strategy`
  branch (`7ce031d`), contains `StandInEngine`, and is the intended substitution
  point for `BrainDrivenEngine` per `PLAN_police_strategy.md` §12 S3a.
