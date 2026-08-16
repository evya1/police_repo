---
id: T022
status: blocked
implementation_state: not_started
priority: P1
task_type: integration
component: system
optional: false
implements:
  - NET-001
  - NET-005
  - SEC-002
  - SEC-005
  - REPORT-009
context_files:
  - docs/PRD.md
  - docs/PLAN.md
  - docs/interop/LEAGUE_COMPATIBILITY.md
  - docs/decisions/ADR-004-operational-interoperability-profile.md
read_set: []
depends_on:
  - T011
  - T012
  - T018
  - T019
gates:
  - id: G-LIVE
    kind: input_gate
    scope: live_interop
    blocks: integration
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

Tests cover derived failure controls without elevating their internal message shapes to official requirements. This task owns the full interoperability/recovery gate named `live_interop`, defined in the project-level integration plan (not duplicated in this repository). `docs/interop/LEAGUE_COMPATIBILITY.md` governs the interoperability conformance work this task performs; it is stage 6 of the verification ladder in `docs/PLAN.md`.

**This task is not the first place low-level vectors run.** Under `ADR-004`, each owning task proves its own compatibility surface at the point it builds it: T005 proves both scent profiles and the selected-model declaration against their conformance vectors, T008 proves its canonical-byte and commit primitives against the published golden vectors, and T009 proves the `reference-v3` tool/argument/turn-order contract locally. This task re-runs those surfaces as a whole system under fault injection and across a full series. A finding here that a single primitive is wrong means an earlier task's suite was incomplete, and the fix belongs there.

## Gates

- `G-LIVE` (`input_gate`, `blocks: integration`) — the task completes locally; it cannot pass the `live_interop` integration gate in the project-level integration plan until this resolves.

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
- [ ] A full series is played end to end against an external uncounted peer — a friendly run, not self-play — and the mutual audit settles clean in both role directions before any counted play is scheduled.
- [ ] Both independently derived result artifacts compare consistently before any send call.

## Verification

- `uv run pytest tests/integration tests/contract`
- `uv run ruff check tests/integration tests/contract`

## Implementation plan

To be completed immediately before execution.

## Handoff contract

Report files changed, tests executed, exact test results, decisions made, deviations, blockers, and newly discovered work. Include command output or artifact paths sufficient for the orchestrator to validate every acceptance criterion.

## Result and evidence
