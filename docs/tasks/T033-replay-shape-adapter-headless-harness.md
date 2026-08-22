---
id: T033
status: not_started
priority: P0
task_type: component
component: C03
optional: false
implements:
  - SEC-005
  - SEC-006
  - OBS-006
context_files:
  - docs/components/C03-peer-protocol-integrity/PRD.md
  - docs/components/C03-peer-protocol-integrity/PLAN.md
  - docs/PRD_replay_port.md
  - docs/PLAN_replay_port.md
read_set: []
depends_on:
  - T008
gates: []
parallel_safe: true
claimed_by:
claim_expires_at:
write_set:
  - common/transport/replay_records.py
  - common/transport/replay.py
  - tests/unit/transport/test_replay_records.py
  - tests/unit/transport/test_replay_verify.py
risk: medium
---

# T033 — Replay shape adapter & headless harness

## Expected outcome

Create the shared adapter and headless verification harness for kit-shaped replay artifacts.

## Requirements implemented

- `SEC-005`
- `SEC-006` (consumed)
- `OBS-006` (verification engine)

## Relevant context

Implements FR-RP-01…03, 08, 09, 10, 13 (shared half). Depends on T008 done.

## Constraints

- Edit only the declared write set.
- `common/` work is written once and synced byte-identical to both repos.

## Acceptance criteria

- `common/transport/replay_records.py` provides `from_kit_record`, `to_kit_record`, `flat_steps_to_kit_doc`, `is_foreign_record` with pure round-trip identity and re-hash-exact.
- `common/transport/replay.py` provides `_terms_beside`, `verify_log`, `verify_dir`, `cross_check_uid` with verdict split TAMPERED/ILLEGAL.
- Tests pass: `tests/unit/transport/test_replay_records.py`, `tests/unit/transport/test_replay_verify.py`.
- Ruff clean, line cap ok, `diff -rq` common/ across repos 0.

## Verification

- `uv run pytest tests/unit/transport/test_replay_records.py tests/unit/transport/test_replay_verify.py`
- `uv run ruff check common/transport tests/unit/transport`
- `diff -rq` common/ across repos

## Result and evidence

(to be filled)
