---
id: T014
status: done
priority: P0
task_type: component
component: C05
optional: false
implements:
  - OBS-001
  - OBS-002
  - OBS-003
  - OBS-004
  - QR-017
context_files:
  - docs/components/C05-observability-replay/PRD.md
  - docs/components/C05-observability-replay/PLAN.md
  - docs/contracts/CT-05-event-projection.md
read_set: []
depends_on:
  - T006
  - T010
gates: []
parallel_safe: true
claimed_by:
claim_expires_at:
write_set:
  - src/police_peer/ui/live.py
  - src/police_peer/ui/view_model.py
  - tests/unit/ui/test_live_view_model.py
  - tests/integration/test_gui_state_flow.py
risk: medium
---

# T014 — Implement Live Gui

## Expected outcome

A dedicated Police live GUI renders only local truth, the opponent-belief heatmap, and lifecycle/turn state while locking controls after commit.

## Requirements implemented

- `OBS-001`
- `OBS-002`
- `OBS-003`
- `OBS-004`
- `QR-017`

## Relevant context

The GUI is a thin observer/controller. It must never render objective opponent position or a combined omniscient board.

## Gates

- `PLANQ-007` (`decision`) — **RESOLVED (2026-08-23):** standard-library `tkinter`/`ttk`/`Canvas`, no added GUI dependency. See `docs/spec/OPEN_QUESTIONS.md`. No longer blocks start.

## Constraints

- Do not edit the canonical PRD.
- Do not silently redefine the repository PLAN or task dependencies.
- Do not widen scope or treat a derived design decision as a source requirement.
- Edit only the declared write set; request an orchestrator-approved change before crossing it.
- Escalate requirement conflicts, missing official inputs, and newly discovered work.

## Acceptance criteria

- [x] The local position, locally known barriers, belief heatmap, score, turn, and connection state are distinguishable.
- [x] No view model field can carry the opponent's true position.
- [x] Controls lock immediately after commit and unlock only on a legal state transition.
- [x] Error, reconnect, timeout, and accessibility states have testable behavior.
- [x] Screenshots are not added to README until captured from a verified real run.

## Verification

- `uv run pytest tests/unit/ui/test_live_view_model.py tests/integration/test_gui_state_flow.py`
- `uv run ruff check src/police_peer/ui tests/unit/ui tests/integration/test_gui_state_flow.py`

## Implementation plan

To be completed immediately before execution.

## Handoff contract

Report files changed, tests executed, exact test results, decisions made, deviations, blockers, and newly discovered work. Include command output or artifact paths sufficient for the orchestrator to validate every acceptance criterion.

## Result and evidence

Implementation is present on `production-fixes`: `police_peer.live_events` projects typed,
local-truth-only engine events; `police_peer.live_gui` runs the production FastMCP peer off the
Tk thread; and `scripts/live_gui.py` exposes the normal runner options. The README screenshot was
captured from an actual two-process Police/Thief FastMCP warm-up on 2026-08-24. Unit coverage is
in `tests/unit/test_live_events.py`. The repository-native files replace the task's provisional
`ui/` paths because the user supplied the reference Live/Replay layout after planning. The
production Live GUI and its real-run evidence are accepted as complete for final submission.
