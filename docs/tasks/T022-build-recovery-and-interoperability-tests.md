---
id: T022
status: blocked
priority: P1
implements:
  - NET-001
  - NET-005
  - SEC-002
  - SEC-005
  - REPORT-009
depends_on:
  - T011
  - T012
  - T018
  - T019
parallel_safe: true
claimed_by:
claim_expires_at:
write_set:
  - tests/integration/test_full_series.py
  - tests/integration/test_recovery_matrix.py
  - tests/contract/test_cross_peer_vectors.py
risk: high
---

# T022 — Build Recovery And Interoperability Tests

## Expected outcome

Two-process contract and fault-injection suites prove lifecycle recovery, deterministic audit closure, and report agreement across clean independent instances.

## Requirements implemented

- `NET-001`
- `NET-005`
- `SEC-002`
- `SEC-005`
- `REPORT-009`

## Relevant context

Tests cover derived failure controls without elevating their internal message shapes to official requirements.

## Constraints

- Do not edit the canonical PRD.
- Do not silently redefine the repository PLAN or task dependencies.
- Do not widen scope or treat a derived design decision as a source requirement.
- Edit only the declared write set; request an orchestrator-approved change before crossing it.
- Escalate requirement conflicts, missing official inputs, and newly discovered work.

## Acceptance criteria

- [ ] Two fresh processes complete a six-sub-game series with no shared memory.
- [ ] Loss, duplicate, reorder, stale step, disconnect, slow response, crash, and restart cases have deterministic outcomes.
- [ ] Audit binds reveals to stored live commitments and rejects fabricated, missing, impossible, or mutated histories.
- [ ] Cross-peer serialization fixtures include Unicode, floats, compact/spaced separators, Nonce placement, and signature-insertion edge cases; production expectations follow only the approved contract.
- [ ] Compatibility failures for report-layout, scent-profile, tie-profile, and draft-versus-send mismatches are detected before counted play.
- [ ] Both independently derived result artifacts compare consistently before any send call.

## Verification

- `uv run pytest tests/integration tests/contract`
- `uv run ruff check tests/integration tests/contract`

## Implementation plan

To be completed immediately before execution.

## Handoff contract

Report files changed, tests executed, exact test results, decisions made, deviations, blockers, and newly discovered work. Include command output or artifact paths sufficient for the orchestrator to validate every acceptance criterion.

## Result and evidence
