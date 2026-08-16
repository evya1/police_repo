---
id: T014
status: blocked
implementation_state: not_started
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
gates:
  - id: PLANQ-007
    kind: decision
    scope: gui_toolkit
    blocks: start
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

- `PLANQ-007` (`decision`, `blocks: start`) — this task cannot be claimed until the gate resolves.

## Constraints

- Do not edit the canonical PRD.
- Do not silently redefine the repository PLAN or task dependencies.
- Do not widen scope or treat a derived design decision as a source requirement.
- Edit only the declared write set; request an orchestrator-approved change before crossing it.
- Escalate requirement conflicts, missing official inputs, and newly discovered work.

## Acceptance criteria

- [ ] The local position, locally known barriers, belief heatmap, score, turn, and connection state are distinguishable.
- [ ] No view model field can carry the opponent's true position.
- [ ] Controls lock immediately after commit and unlock only on a legal state transition.
- [ ] Error, reconnect, timeout, and accessibility states have testable behavior.
- [ ] Screenshots are not added to README until captured from a verified real run.

## Verification

- `uv run pytest tests/unit/ui/test_live_view_model.py tests/integration/test_gui_state_flow.py`
- `uv run ruff check src/police_peer/ui tests/unit/ui tests/integration/test_gui_state_flow.py`

## Implementation plan

To be completed immediately before execution.

## Handoff contract

Report files changed, tests executed, exact test results, decisions made, deviations, blockers, and newly discovered work. Include command output or artifact paths sufficient for the orchestrator to validate every acceptance criterion.

## Result and evidence
