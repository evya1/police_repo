---
id: T034
status: not_started
priority: P0
task_type: component
component: C03
optional: false
implements:
  - OBS-006
  - SEC-005
  - SEC-006
context_files:
  - docs/components/C03-peer-protocol-integrity/PRD.md
  - docs/components/C03-peer-protocol-integrity/PLAN.md
  - docs/PRD_replay_port.md
  - docs/PLAN_replay_port.md
read_set: []
depends_on:
  - T008
gates: []
parallel_safe: true
claimed_by:
claim_expires_at:
write_set:
  - common/transport/subgame.py
  - common/transport/series.py
  - tests/unit/transport/test_series_evidence.py
risk: medium
---

# T034 — Per-subgame evidence capture in the series engine

## Expected outcome

Add `SubGameEvidence` dataclass and propagate evidence through `SeriesResult`.

## Requirements implemented

- `OBS-006` (evidence availability)
- `SEC-005`/`SEC-006` (consumed)

## Relevant context

D-08 seam. `play_subgame` returns evidence; `SeriesResult.evidence` is additive.

Ownership note: `common/transport/subgame.py` and `common/transport/series.py` were modified by ST-09 outside T008's declared write set (see T008 deviations). T034 claims unambiguous ownership for evidence capture changes to these paths.

## Constraints

- Edit only declared write set.
- Source-compatible; existing tests stay green.

## Acceptance criteria

- `common/transport/subgame.py` adds `SubGameEvidence` dataclass; `play_subgame` returns it.
- `common/transport/series.py` adds `SeriesResult.evidence` field; `PeerFacade.run` accumulates.
- `tests/unit/transport/test_series_evidence.py` passes; records re-hash clean; `played` map not in evidence.

## Verification

- `uv run pytest tests/unit/transport tests/integration`
- `uv run ruff check common/transport tests/unit/transport`
- `diff -rq` common/ across repos

## Result and evidence

(to be filled)
