---
id: T008
status: blocked
implementation_state: not_started
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
  - docs/decisions/ADR-004-operational-interoperability-profile.md
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

The minimum committed semantics are State, Move, Intent, and Nonce. OPEN-007 blocks the final *official* byte envelope, including nonce placement, Unicode escaping, separators, and report-consensus scope, and it stays open. Auxiliary serializers and vectors are not official schema evidence and never become one.

Two different claims must not be confused. "These bytes are the officially required bytes" waits on OPEN-007. "These bytes are produced deterministically and identically by both peers" does not — it is a checkable property of the primitives this task builds. This task proves the second claim now rather than deferring every byte check to T022, and proving it changes nothing about OPEN-007's official status.

The byte contract this task implements is the operational convention recorded in `docs/contracts/CT-04-canonical-bytes.md`:

- **Canonical serialization** — UTF-8 without a byte-order mark; object keys sorted by Unicode code point; compact `,` and `:` separators with no other whitespace; non-ASCII emitted literally rather than `\u`-escaped; floats in the shortest exactly round-tripping form, with a value that fails round-trip rejected rather than reformatted; integers and floats kept distinct; no trailing newline.
- **Commitment construction** — `SHA-256( canonical(payload) || "|" || nonce )` over the `{State, Move, Intent}` triple, with `"|"` the single byte U+007C, carried and compared as 64-character lowercase hexadecimal.
- **Ordering** — commit, then acknowledgement, then reveal, then the full audit after the last reveal of a sub-game; the nonce is never transmitted or logged before the audit phase.
- **Identifiers** — `game_uid` is series-scoped, `game_id` sub-game-scoped, both compared as exact strings and produced through the adapter boundary.

There is exactly one canonicalization path in the repository. A second serializer, even a convenience one, is a defect.

This task does **not** own scent arithmetic. Scent profiles and their vectors belong to T005.

## Gates

- `OPEN-007` (`open`, `blocks: criterion`) — the task may be claimed and implemented now; only the acceptance criterion scoped `cross_peer_vectors`, which concerns the official envelope, waits. The early golden-vector criterion below is not gated by it.

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
- [ ] Deterministic golden vectors committed with this task cover, and pass byte-for-byte within this task's own suite: key ordering; compact separators; literal non-ASCII output including non-BMP characters; absence of a trailing newline; float shortest round-trip acceptance and the rejection of a value that fails it; the commit construction including the single-pipe nonce separator and lowercase hexadecimal output; and the same construction applied to the terms and identifier signatures built on it. `{#early_byte_vectors}`
- [ ] Commit, acknowledgement, reveal, and audit ordering is asserted, and an out-of-order reveal is rejected.
- [ ] Tamper detection is proven by a one-byte mutation of each of state, move, intent, and nonce, and by a missing, extra, and reordered step during replay.
- [ ] Both role repositories run the same committed vectors and produce identical results.
- [ ] Differential fixtures cover compact/spaced JSON, Nonce inside/appended, Unicode, floats, key order, signature insertion, replay, step order, and Nonce tampering; only the OPEN-007-approved form is enabled for production. `{#cross_peer_vectors}`

## Verification

- `uv run pytest tests/unit/integrity tests/contract/test_commit_reveal.py`
- `uv run ruff check src/police_peer/integrity tests/unit/integrity tests/contract/test_commit_reveal.py`

## Implementation plan

To be completed immediately before execution.

## Handoff contract

Report files changed, tests executed, exact test results, decisions made, deviations, blockers, and newly discovered work. Include command output or artifact paths sufficient for the orchestrator to validate every acceptance criterion.

## Result and evidence
