---
id: T030
status: ready
priority: P1
task_type: component
component: C04
optional: false
implements: []
context_files:
  - docs/components/C04-runtime-reliability/PRD.md
  - docs/components/C04-runtime-reliability/PLAN.md
read_set:
  - common/transport/subgame.py
  - common/transport/series.py
  - common/domain/scoring.py
  - tests/integration/test_series_loopback.py
  - tests/integration/test_series_fault_audit.py
depends_on: []
gates: []
parallel_safe: true
claimed_by: zed-agent
claim_expires_at: 2026-08-18T23:00:00Z
write_set:
  - common/transport/state.py
  - common/transport/subgame_fsm.py
  - common/transport/series.py
  - tests/unit/transport/test_state.py
  - tests/unit/transport/test_subgame_fsm.py
  - tests/integration/test_fsm_parity.py
  - docs/tasks/T030-port-fsm-alternative-driver.md
risk: low
---
# T030 — Port the kit state machine as an alternative subgame driver

## Expected outcome

A state-machine-guarded subgame driver selectable via `run_series(subgame_driver=...)`, producing
byte-identical ledgers to the legacy driver, with default OFF (legacy behaviour unchanged).

## Acceptance criteria

1. `state.py` is a verbatim port of the kit source, with two deviations: docstring and `Enum` →
   `StrEnum` (repo convention).
2. Parity tests green — clean and fault-injected.
3. Default `run_series` behavior unchanged — the existing test suite passes without modification.
4. `common/` is byte-identical across both repos.
5. Full gate green in both repos.
