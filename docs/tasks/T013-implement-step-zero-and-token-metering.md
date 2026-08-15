---
id: T013
status: blocked
priority: P0
implements:
  - SEC-008
  - SEC-009
  - LEAGUE-007
  - QR-018
depends_on:
  - T008
  - T010
parallel_safe: true
claimed_by:
claim_expires_at:
write_set:
  - src/police_peer/evidence/
  - tests/unit/evidence/
risk: medium
---

# T013 — Implement Step Zero And Token Metering

## Expected outcome

Signed Step 0 captures the required reproducibility declaration, and token metering records per-sub-game and per-series totals without inventing a fairness formula.

## Requirements implemented

- `SEC-008`
- `SEC-009`
- `LEAGUE-007`
- `QR-018`

## Relevant context

Hardware, model, code, team, sub-game, and Git commit fields are required. Cost tracking applies only when a paid API is used.

## Constraints

- Do not edit the canonical PRD.
- Do not silently redefine the repository PLAN or task dependencies.
- Do not widen scope or treat a derived design decision as a source requirement.
- Edit only the declared write set; request an orchestrator-approved change before crossing it.
- Escalate requirement conflicts, missing official inputs, and newly discovered work.

## Acceptance criteria

- [ ] All required Step 0 fields are collected before the first move and signed through the integrity boundary.
- [ ] Missing or unverifiable Git commit/config version blocks counted play.
- [ ] Token input/output usage is aggregated per sub-game and series and included in artifacts.
- [ ] No lecturer-side normalization formula is recreated locally.
- [ ] Tests use deterministic system-info and usage adapters without exposing host secrets.

## Verification

- `uv run pytest tests/unit/evidence/test_step_zero.py tests/unit/evidence/test_tokens.py`
- `uv run ruff check src/police_peer/evidence tests/unit/evidence`

## Implementation plan

To be completed immediately before execution.

## Handoff contract

Report files changed, tests executed, exact test results, decisions made, deviations, blockers, and newly discovered work. Include command output or artifact paths sufficient for the orchestrator to validate every acceptance criterion.

## Result and evidence
