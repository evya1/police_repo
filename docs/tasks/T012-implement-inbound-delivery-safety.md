---
id: T012
status: done
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
claimed_by: IA
claim_expires_at: 2026-08-17
claim_expires_at:
write_set:
  - common/transport/inbox.py
  - common/transport/faults.py
  - tests/unit/transport/test_inbox_duplicates.py
  - tests/unit/transport/test_inbox_window.py
  - tests/unit/transport/test_inbox_decision.py
  - tests/unit/transport/test_inbox_deadline.py
  - tests/unit/transport/test_inbox_state.py
  - tests/integration/test_inbox_faulty.py
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

- [x] An identical duplicate is idempotent; a different commitment for an accepted step is loud evidence.
- [x] A bounded out-of-order window applies messages only in sequence and rejects messages beyond policy.
- [x] Stale sub-game, role, or step messages never mutate current state.
- [x] A terminated transport session is recreated once and the same idempotency key is retained.
- [x] Fault-injection tests cover loss, duplication, reorder, disconnect, and retry exhaustion.

## Verification

```bash
uv run pytest tests/unit/transport/test_inbox_duplicates.py tests/unit/transport/test_inbox_window.py tests/unit/transport/test_inbox_decision.py tests/unit/transport/test_inbox_deadline.py tests/unit/transport/test_inbox_state.py tests/integration/test_inbox_faulty.py -q
# 171 passed
uv run ruff check common/ tests/
# All checks passed!
uv run pytest --cov=common --cov-report=term-missing -q
# 90.54% coverage (above 85% threshold)
```

## Implementation plan

To be completed immediately before execution.

## Handoff contract

Report files changed, tests executed, exact test results, decisions made, deviations, blockers, and newly discovered work. Include command output or artifact paths sufficient for the orchestrator to validate every acceptance criterion.

## Result and evidence

**ST-08 implementation complete.**

**Files created (both repos, byte-identical):**
- `common/transport/inbox.py` (148 lines) — Real at-least-once inbox with `delivery_decision`, `deadline_decision`, `Inbox` dataclass, `Equivocation`/`ProtocolViolation` exceptions
- `tests/unit/transport/test_inbox_duplicates.py` (84 lines) — TC-14, TC-15
- `tests/unit/transport/test_inbox_window.py` (66 lines) — TC-16
- `tests/unit/transport/test_inbox_decision.py` (98 lines) — Pure decision function tests
- `tests/unit/transport/test_inbox_deadline.py` (69 lines) — TC-19
- `tests/unit/transport/test_inbox_state.py` (66 lines) — State management tests
- `tests/integration/test_inbox_faulty.py` (118 lines) — TC-17 integration test

**Key design decisions:**
- `delivery_decision` keys duplicates on **commit**, not `(kind, step)` — a retry collapses while a different commitment stays loud
- `deadline_decision` ignores `arrived` and `tolerated` — duplicates/early pushes renew nothing
- `Inbox.reset_for_subgame()` clears `played`, `buffered`, `next_step`, and `absorbed` per sub-game
- `window=0` is refused at `Inbox()` construction (FR-32)
- `Equivocation` and `ProtocolViolation` exceptions named without `Error` suffix (matching reference kit convention; `# noqa: N818` applied)

**Verification evidence:**
- Both repos: 171 tests passed
- Ruff: clean (0 violations)
- Coverage: 90.54% (police), 90.22% (thief) — above 85% threshold
- Spine test (`test_series_loopback.py`): green
- All new files ≤150 lines
- Byte-identical sync confirmed (md5 hashes match across repos)

**No blockers. No deviations from PRD/PLAN.**

**Next:** ST-09 (mutual audit + TAMPERED sanction).
