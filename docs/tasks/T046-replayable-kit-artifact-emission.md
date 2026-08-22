---
id: T046
status: not_started
priority: P0
task_type: component
component: C06
optional: false
implements:
  - REPORT-005
  - REPORT-006
  - REPORT-007
  - REPORT-008
  - REPORT-009
  - OBS-006
context_files:
  - docs/components/C06-reporting-league/PRD.md
  - docs/components/C06-reporting-league/PLAN.md
  - docs/PRD_replay_port.md
  - docs/PLAN_replay_port.md
read_set: []
depends_on:
  - T033
  - T034
gates: []
parallel_safe: true
claimed_by:
claim_expires_at:
write_set:
  - src/police_peer/reporting/pipeline.py
  - src/police_peer/runner.py
  - tests/unit/reporting/test_kit_artifacts.py
  - tests/integration/test_replayable_bundle.py
risk: medium
---

# T046 — Replayable kit-shaped artifact emission, interop boundary

## Expected outcome

Extend reporting pipeline to emit kit-shaped replayable bundle under `replay/` with interop label.

## Requirements implemented

- `REPORT-005..REPORT-009` (consumed via interop)
- `OBS-006` (artifact availability)

## Relevant context

D-02 interop boundary. Not gated by INPUT-001/T016.

## Constraints

- Edit only declared write set per repo.

## Acceptance criteria

- `src/police_peer/reporting/pipeline.py` extends `KitInteropAdapter` with interop docs and `write_replayable_bundle`.
- `src/police_peer/runner.py` emits bundle when evidence present.
- Tests pass, artifacts written to `artifacts/replay/`, canonical bytes with trailing newline.

## Verification

- `uv run pytest tests/unit/reporting tests/integration/test_replayable_bundle.py`
- `uv run ruff check src/police_peer/reporting src/police_peer/runner.py tests/unit/reporting`
- Real warmup run produces `artifacts/replay/`.

## Result and evidence

(to be filled)
