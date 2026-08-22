---
id: T036
status: not_started
priority: P0
task_type: component
component: C05
optional: false
implements:
  - OBS-006
  - OBS-007
context_files:
  - docs/components/C05-observability-replay/PRD.md
  - docs/components/C05-observability-replay/PLAN.md
  - docs/PRD_replay_port.md
  - docs/PLAN_replay_port.md
read_set: []
depends_on:
  - T033
  - T035
gates: []
parallel_safe: true
claimed_by:
claim_expires_at:
write_set:
  - scripts/replay.py
  - tests/integration/test_replay_tamper.py
  - docs/evidence/replay-port/
risk: medium
---

# T036 — Headless replay CLI, integration & tamper evidence

## Expected outcome

Headless CLI for offline verification and integration tests with tamper evidence.

## Requirements implemented

- `OBS-006` (rule-20 gate exercised)
- `OBS-007` (evidence honesty)

## Relevant context

Implements FR-RP-07.

## Constraints

- Edit only declared write set.

## Acceptance criteria

- `scripts/replay.py` implements `replay <dir>` with per-log verdicts, uid check, exit code.
- `tests/integration/test_replay_tamper.py` covers TC-RP-02, TC-RP-05, TC-RP-10 and CLI exit codes.
- `docs/evidence/replay-port/verified_ok/` and `tampered/` exist with transcripts.

## Verification

- `uv run pytest tests/integration/test_replay_tamper.py`
- `uv run python scripts/replay.py <evidence>/verified_ok` exit 0
- `uv run python scripts/replay.py <evidence>/tampered` exit 1
- Full gates green.

## Result and evidence

(to be filled)
