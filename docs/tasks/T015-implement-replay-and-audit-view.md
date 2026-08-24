---
id: T015
status: done
priority: P0
task_type: component
component: C05
optional: false
implements:
  - OBS-005
  - OBS-006
  - SEC-005
  - SEC-006
context_files:
  - docs/components/C05-observability-replay/PRD.md
  - docs/components/C05-observability-replay/PLAN.md
read_set: []
depends_on:
  - T008
  - T010
  - T014
  - T047
gates: []
parallel_safe: true
claimed_by:
claim_expires_at:
write_set:
  - src/police_peer/ui/replay.py
  - tests/unit/replay/
risk: high
---

# T015 — Implement Replay And Audit View

## Expected outcome

Replay loads a final log, navigates in both directions, recomputes every commitment, and visibly distinguishes Verified OK from TAMPERED.

## Requirements implemented

- `OBS-005`
- `OBS-006`
- `SEC-005`
- `SEC-006`

## Relevant context

Replay is evidence, not a second rules engine. It consumes immutable artifacts and uses the same audited domain/integrity paths as live settlement.

## Constraints

- Do not edit the canonical PRD.
- Do not silently redefine the repository PLAN or task dependencies.
- Do not widen scope or treat a derived design decision as a source requirement.
- Edit only the declared write set; request an orchestrator-approved change before crossing it.
- Escalate requirement conflicts, missing official inputs, and newly discovered work.

## Acceptance criteria

- [x] Forward and backward navigation is deterministic and side-effect free.
- [x] Each displayed step shows its verification result from recomputation.
- [x] A single altered payload, nonce, commitment, missing step, or impossible transition fails the game.
- [x] Unknown optional fields degrade to visible unsupported evidence rather than false tamper accusations.
- [x] A genuine Verified OK screenshot remains a submission-time evidence task.

## Verification

- `uv run pytest tests/unit/replay`
- `uv run ruff check src/police_peer/ui/replay.py tests/unit/replay`

## Implementation plan

To be completed immediately before execution.

## Handoff contract

Report files changed, tests executed, exact test results, decisions made, deviations, blockers, and newly discovered work. Include command output or artifact paths sufficient for the orchestrator to validate every acceptance criterion.

## Orchestrator note (ORC-R0)

T015 now depends on **T047**, not T033: the replay application service and SDK are the only
supported entry point. The GUI adapter consumes `BundleReplayReport` / `ReplayReport` and contains
**no hashing, no config/log pairing, and no schema logic** of its own. It renders every verdict,
every coverage layer, and the external-authenticity status as supplied by the service.

## Result and evidence

Completed on `production-fixes`. `police_peer.replay_gui` selects repository-native league-kit
logs, verifies both sealed halves before display, and refuses tampered evidence; the Tk facade is
read-only and provides deterministic previous/next navigation over verified records. Honest and
tampered behavior is covered by `tests/integration/test_replay_gui_adapter.py`, and the README uses
a genuine Verified OK screenshot captured from the working viewer.
