---
id: T008
status: blocked
priority: P0
task_type: component
component: C03
optional: false
implements:
  - SEC-001
  - SEC-002
  - SEC-003
  - SEC-004
  - SEC-005
  - SEC-006
  - SEC-007
context_files:
  - docs/components/C03-peer-protocol-integrity/PRD.md
  - docs/components/C03-peer-protocol-integrity/PLAN.md
  - docs/mechanisms/M-05-commit-reveal-integrity.md
  - docs/contracts/CT-04-canonical-bytes.md
read_set: []
depends_on:
  - T003
gates:
  - id: OPEN-007
    kind: open
    scope: cross_peer_vectors
    blocks: criterion
parallel_safe: true
claimed_by:
claim_expires_at:
write_set:
  - src/police_peer/integrity/commit_reveal.py
  - src/police_peer/integrity/audit.py
  - tests/unit/integrity/
  - tests/contract/test_commit_reveal.py
risk: high
---

# T008 — Implement Integrity Core

## Expected outcome

A single integrity boundary creates fresh nonces, performs SHA-256 Commit-Reveal, retains received commitments, and verifies complete reveals without ambiguous parallel hash paths.

## Requirements implemented

- `SEC-001`
- `SEC-002`
- `SEC-003`
- `SEC-004`
- `SEC-005`
- `SEC-006`
- `SEC-007`

## Relevant context

The minimum committed semantics are State, Move, Intent, and Nonce. OPEN-007 blocks the final byte envelope, including nonce placement, Unicode escaping, separators, and report-consensus scope. Auxiliary serializers and vectors may suggest tests but are not official schema evidence.

## Gates

- `OPEN-007` (`open`, `blocks: criterion`) — the task may be claimed and implemented now; only the acceptance criterion scoped `cross_peer_vectors` waits.

## Constraints

- Do not edit the canonical PRD.
- Do not silently redefine the repository PLAN or task dependencies.
- Do not widen scope or treat a derived design decision as a source requirement.
- Edit only the declared write set; request an orchestrator-approved change before crossing it.
- Escalate requirement conflicts, missing official inputs, and newly discovered work.

## Acceptance criteria

- [ ] Every step uses a fresh cryptographic nonce that is never transmitted before final reveal.
- [ ] Commit, acknowledgement, reveal, and final audit ordering is explicit.
- [ ] Audit compares reveals to commitments retained from live play, detects missing/extra/mutated steps, and checks legal state progression.
- [ ] One hash mismatch yields an immutable TAMPERED result and no repair path.
- [ ] Differential fixtures cover compact/spaced JSON, Nonce inside/appended, Unicode, floats, key order, signature insertion, replay, step order, and Nonce tampering; only the OPEN-007-approved form is enabled for production. `{#cross_peer_vectors}`

## Verification

- `uv run pytest tests/unit/integrity tests/contract/test_commit_reveal.py`
- `uv run ruff check src/police_peer/integrity tests/unit/integrity tests/contract/test_commit_reveal.py`

## Implementation plan

To be completed immediately before execution.

## Handoff contract

Report files changed, tests executed, exact test results, decisions made, deviations, blockers, and newly discovered work. Include command output or artifact paths sufficient for the orchestrator to validate every acceptance criterion.

## Result and evidence
