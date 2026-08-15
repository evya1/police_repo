---
id: T015
status: blocked
priority: P0
implements:
  - OBS-005
  - OBS-006
  - SEC-005
  - SEC-006
depends_on:
  - T008
  - T010
  - T014
parallel_safe: true
claimed_by:
claim_expires_at:
write_set:
  - src/police_peer/ui/replay.py
  - tests/unit/replay/
  - tests/integration/test_replay_tamper.py
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

- [ ] Forward and backward navigation is deterministic and side-effect free.
- [ ] Each displayed step shows its verification result from recomputation.
- [ ] A single altered payload, nonce, commitment, missing step, or impossible transition fails the game.
- [ ] Unknown optional fields degrade to visible unsupported evidence rather than false tamper accusations.
- [ ] A genuine Verified OK screenshot remains a submission-time evidence task.

## Verification

- `uv run pytest tests/unit/replay tests/integration/test_replay_tamper.py`
- `uv run ruff check src/police_peer/ui/replay.py tests/unit/replay tests/integration/test_replay_tamper.py`

## Implementation plan

To be completed immediately before execution.

## Handoff contract

Report files changed, tests executed, exact test results, decisions made, deviations, blockers, and newly discovered work. Include command output or artifact paths sufficient for the orchestrator to validate every acceptance criterion.

## Result and evidence
