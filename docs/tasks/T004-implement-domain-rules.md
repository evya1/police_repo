---
id: T004
status: blocked
priority: P0
implements:
  - GAME-001
  - GAME-002
  - GAME-003
  - GAME-004
  - GAME-005
  - GAME-006
  - GAME-007
  - GAME-008
  - GAME-009
  - GAME-010
  - GAME-011
  - GAME-012
  - GAME-013
  - GAME-014
depends_on:
  - T003
parallel_safe: true
claimed_by:
claim_expires_at:
write_set:
  - src/police_peer/domain/board.py
  - src/police_peer/domain/rules.py
  - src/police_peer/domain/scoring.py
  - tests/unit/domain/test_board.py
  - tests/unit/domain/test_rules.py
  - tests/unit/domain/test_scoring.py
risk: high
---

# T004 — Implement Domain Rules

## Expected outcome

Pure deterministic board, movement, barrier, capture, terminal-condition, and scoring logic implements the binding rules and rejects illegal actions.

## Requirements implemented

- `GAME-001`
- `GAME-002`
- `GAME-003`
- `GAME-004`
- `GAME-005`
- `GAME-006`
- `GAME-007`
- `GAME-008`
- `GAME-009`
- `GAME-010`
- `GAME-011`
- `GAME-012`
- `GAME-013`
- `GAME-014`

## Relevant context

Rules must operate only on role-local truth. The fixed scoring table and configured Minimum/Negotiated bounds are inputs, not hard-coded alternative values.

## Constraints

- Do not edit the canonical PRD.
- Do not silently redefine the repository PLAN or task dependencies.
- Do not widen scope or treat a derived design decision as a source requirement.
- Edit only the declared write set; request an orchestrator-approved change before crossing it.
- Escalate requirement conflicts, missing official inputs, and newly discovered work.

## Acceptance criteria

- [ ] Property and example tests cover boundaries, cardinal moves, STAY, and diagonal rejection.
- [ ] Barrier placement, persistence, quota, collision, and trapped-Thief capture follow the official rules.
- [ ] A Police capture claim names its current post-move cell; arbitrary-cell claims are rejected, Thief responses are truth-checked, and all fixed scores are deterministic.
- [ ] Move-cap and survival termination use the signed configuration.
- [ ] No network, GUI, LLM, clock, or filesystem dependency enters domain logic.

## Verification

- `uv run pytest tests/unit/domain/test_board.py tests/unit/domain/test_rules.py tests/unit/domain/test_scoring.py`
- `uv run ruff check src/police_peer/domain tests/unit/domain`

## Implementation plan

To be completed immediately before execution.

## Handoff contract

Report files changed, tests executed, exact test results, decisions made, deviations, blockers, and newly discovered work. Include command output or artifact paths sufficient for the orchestrator to validate every acceptance criterion.

## Result and evidence
