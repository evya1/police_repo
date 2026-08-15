---
id: T011
status: blocked
priority: P0
task_type: component
component: C04
optional: false
implements:
  - ARCH-008
  - NET-005
  - CFG-007
  - CFG-008
context_files:
  - docs/components/C04-runtime-reliability/PRD.md
  - docs/components/C04-runtime-reliability/PLAN.md
read_set: []
depends_on:
  - T010
gates: []
parallel_safe: true
claimed_by:
claim_expires_at:
write_set:
  - src/police_peer/reliability/
  - tests/unit/reliability/
risk: high
---

# T011 — Implement Deadlines Retry And Watchdog

## Expected outcome

Every outbound request has an immutable deadline and bounded retry policy, while an independent watchdog persists safe state and shuts down controlledly on stalls.

## Requirements implemented

- `ARCH-008`
- `NET-005`
- `CFG-007`
- `CFG-008`

## Relevant context

Retries must not renew the original obligation indefinitely. Appendix F supplies defaults/statuses; approved configuration controls actual values. The source requires an independent background watchdog behavior, heartbeat, persistence, and controlled shutdown; it does not mandate a particular Python thread/process class, so execution mechanics are chosen immediately before implementation while preserving independence.

## Constraints

- Do not edit the canonical PRD.
- Do not silently redefine the repository PLAN or task dependencies.
- Do not widen scope or treat a derived design decision as a source requirement.
- Edit only the declared write set; request an orchestrator-approved change before crossing it.
- Escalate requirement conflicts, missing official inputs, and newly discovered work.

## Acceptance criteria

- [ ] Each request carries timestamp and expiry and cannot be renewed by unrelated traffic.
- [ ] Retry count/backoff are bounded and expiry resolves to an explicit technical-loss path.
- [ ] Watchdog heartbeat and request deadlines use injectable clocks for deterministic tests.
- [ ] A stall snapshot excludes secrets and opponent hidden truth.
- [ ] Stop/restart paths release waiting resources and preserve the last safe state.

## Verification

- `uv run pytest tests/unit/reliability`
- `uv run ruff check src/police_peer/reliability tests/unit/reliability`

## Implementation plan

To be completed immediately before execution.

## Handoff contract

Report files changed, tests executed, exact test results, decisions made, deviations, blockers, and newly discovered work. Include command output or artifact paths sufficient for the orchestrator to validate every acceptance criterion.

## Result and evidence
