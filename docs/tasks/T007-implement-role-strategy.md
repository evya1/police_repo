---
id: T007
status: blocked
implementation_state: not_started
priority: P0
task_type: component
component: C02
optional: false
implements:
  - ARCH-007
  - STRAT-007
  - STRAT-008
  - STRAT-009
context_files:
  - docs/components/C02-perception-strategy/PRD.md
  - docs/components/C02-perception-strategy/PLAN.md
  - docs/mechanisms/M-03-police-strategy.md
read_set: []
depends_on:
  - T004
  - T006
gates:
  - id: PLANQ-008
    kind: decision
    scope: heuristics
    blocks: criterion
parallel_safe: true
claimed_by:
claim_expires_at:
write_set:
  - src/police_peer/strategy/
  - tests/unit/strategy/
risk: medium
---

# T007 — Implement Role Strategy

## Expected outcome

A deterministic Police policy uses belief and legal actions while keeping verbal hint generation separate from movement selection.

## Requirements implemented

- `ARCH-007`
- `STRAT-007`
- `STRAT-008`
- `STRAT-009`

## Relevant context

RL is optional. The recommended zero-token `template` mode is a valid default and a live LLM provider is not a mandatory acceptance criterion. Movement stays algorithmic; if an LLM is used, it may draft/analyze text only unless a mutually documented exception is approved and legality remains locally validated.

## Gates

- `PLANQ-008` (`decision`, `blocks: criterion`) — the task may be claimed and implemented now; only the acceptance criterion scoped `heuristics` waits.

## Constraints

- Do not edit the canonical PRD.
- Do not silently redefine the repository PLAN or task dependencies.
- Do not widen scope or treat a derived design decision as a source requirement.
- Edit only the declared write set; request an orchestrator-approved change before crossing it.
- Escalate requirement conflicts, missing official inputs, and newly discovered work.

## Acceptance criteria

- [ ] The policy ranks only legal actions from role-local state and belief.
- [ ] The Police objective is explicit: use belief to pursue, choose between legal movement and barrier placement, and issue capture claims only when locally justified, per the approved PLANQ-008 heuristic priorities and seeded scenarios. `{#heuristics}`
- [ ] Hint generation enforces the negotiated arena and word cap while allowing truth or deception.
- [ ] Template mode works without model/network dependencies; any optional provider is isolated behind the text boundary.
- [ ] A slow or failed text generator cannot block or select the movement action.
- [ ] Strategy tests are seeded and reproducible; no unclaimed learning result is documented.

## Verification

- `uv run pytest tests/unit/strategy`
- `uv run ruff check src/police_peer/strategy tests/unit/strategy`

## Implementation plan

To be completed immediately before execution.

## Handoff contract

Report files changed, tests executed, exact test results, decisions made, deviations, blockers, and newly discovered work. Include command output or artifact paths sufficient for the orchestrator to validate every acceptance criterion.

## Result and evidence
