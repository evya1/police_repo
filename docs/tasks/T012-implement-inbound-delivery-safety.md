---
id: T012
status: blocked
priority: P1
task_type: component
component: C03
optional: false
implements:
  - NET-005
  - SEC-002
  - SEC-005
context_files:
  - docs/components/C03-peer-protocol-integrity/PRD.md
  - docs/components/C03-peer-protocol-integrity/PLAN.md
read_set: []
depends_on:
  - T009
  - T010
gates: []
parallel_safe: true
claimed_by:
claim_expires_at:
write_set:
  - common/transport/inbox.py
  - common/transport/faults.py
  - tests/unit/transport/test_inbox.py
  - tests/integration/test_delivery_faults.py
risk: high
---

# T012 — Implement Inbound Delivery Safety

## Expected outcome

The peer safely absorbs exact redelivery, detects equivocation, bounds reordering, and re-establishes a dropped session once without duplicating state changes.

## Requirements implemented

- `NET-005`
- `SEC-002`
- `SEC-005`

## Relevant context

This is a derived reliability decision supporting retries and auditability. It does not define new official protocol fields or sanctions.

## Constraints

- Do not edit the canonical PRD.
- Do not silently redefine the repository PLAN or task dependencies.
- Do not widen scope or treat a derived design decision as a source requirement.
- Edit only the declared write set; request an orchestrator-approved change before crossing it.
- Escalate requirement conflicts, missing official inputs, and newly discovered work.

## Acceptance criteria

- [ ] An identical duplicate is idempotent; a different commitment for an accepted step is loud evidence.
- [ ] A bounded out-of-order window applies messages only in sequence and rejects messages beyond policy.
- [ ] Stale sub-game, role, or step messages never mutate current state.
- [ ] A terminated transport session is recreated once and the same idempotency key is retained.
- [ ] Fault-injection tests cover loss, duplication, reorder, disconnect, and retry exhaustion.

## Verification

- `uv run pytest tests/unit/transport/test_inbox.py tests/integration/test_delivery_faults.py`
- `uv run ruff check src/police_peer/transport/inbox.py tests/unit/transport/test_inbox.py tests/integration/test_delivery_faults.py`

## Implementation plan

To be completed immediately before execution.

## Handoff contract

Report files changed, tests executed, exact test results, decisions made, deviations, blockers, and newly discovered work. Include command output or artifact paths sufficient for the orchestrator to validate every acceptance criterion.

## Result and evidence
