---
id: T013
status: blocked
implementation_state: not_started
priority: P0
task_type: component
component: C03
optional: false
implements:
  - SEC-008
  - SEC-009
  - LEAGUE-007
  - QR-018
context_files:
  - docs/components/C03-peer-protocol-integrity/PRD.md
  - docs/components/C03-peer-protocol-integrity/PLAN.md
read_set: []
depends_on:
  - T008
  - T010
gates:
  - id: INPUT-003
    kind: input
    scope: step_zero_key
    blocks: criterion
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

No course-supplied Step 0 signing credential is known to exist, and none may be assumed, fabricated, generated as a stand-in, or committed. OPEN-006 asks only whether such a credential is required at all.

Implement Step 0 against the documented project mechanism: collect the required fields before the first move, canonicalize them under the `docs/contracts/CT-04-canonical-bytes.md` convention, and seal them through the single integrity boundary owned by T008. Supply the signing material through one narrow, injected credential seam with **no default value**, so that if an authoritative credential requirement later appears it is satisfied by configuring that seam rather than by changing the Step 0 record or the integrity path.

## Gates

- `INPUT-003` (`input`, `blocks: criterion`) — the task may be claimed and implemented now; only the acceptance criterion scoped `step_zero_key` waits.

## Constraints

- Do not edit the canonical PRD.
- Do not silently redefine the repository PLAN or task dependencies.
- Do not widen scope or treat a derived design decision as a source requirement.
- Edit only the declared write set; request an orchestrator-approved change before crossing it.
- Escalate requirement conflicts, missing official inputs, and newly discovered work.

## Acceptance criteria

- [ ] All required Step 0 fields are collected before the first move and sealed through the integrity boundary using the documented project mechanism.
- [ ] The signing material reaches the Step 0 path through one injected seam with no default and no committed value; a test proves the seam is injected rather than defaulted.
- [ ] If OPEN-006 resolves to require a course-supplied credential, that credential is configured through the existing seam with no change to the Step 0 record shape or the integrity path. `{#step_zero_key}`
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
