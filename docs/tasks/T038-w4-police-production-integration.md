---
id: T038
status: blocked
priority: P0
task_type: component
component: C02
optional: false
implements:
  - S3a
  - S3b
  - S3c
  - M-03
  - H2
  - H3
  - H4
  - H5
context_files:
  - docs/mechanisms/M-03-police-strategy.md
  - docs/tasks/T007-extend-wire-brain-swap.md
  - docs/tasks/T007-extend-kpi-harness.md
read_set:
  - src/police_peer/wire/__init__.py
  - src/police_peer/sdk.py
depends_on:
  - T037
gates: []
parallel_safe: false
claimed_by:
claim_expires_at:
write_set:
  - src/police_peer/wire/__init__.py
  - src/police_peer/sdk.py
  - src/police_peer/wire/evidence.py
  - tests/unit/wire/
  - tests/integration/test_strategy_selfplay_kpi.py
risk: medium
---

# T038 — Wave W4b: Police Production-Integration (police_repo)

Mirrors the shape of `thief_repo`'s `T038`/PR #36 outcome, but this is a **real
implementation task** here, not a verification record — police_repo has not yet wired a
real brain into production the way thief_repo's PR #36 did.

## Expected outcome

- `sdk.py`'s `create_peer` returns a brain-driven engine for the POLICE role by default
  (real `PoliceBrain`/strategy from `T037`, not a stand-in).
- The write-set extensions already pre-approved in `T007-extend-wire-brain-swap` (the
  `BrainDrivenEngine` seam in `src/police_peer/wire/__init__.py`) and
  `T007-extend-kpi-harness` (`tests/integration/test_strategy_selfplay_kpi.py`) are used
  as-is; this task does not re-litigate those extensions.
- Wire-boundary evidence normalization exists for untrusted inbound smell/hint data before
  it reaches belief/brain (mirrors thief_repo's H3 `wire/evidence.py`).
- KPI harness evaluates every POLICE sub-game across a series against a capturing-capable
  opponent, with an always-STAY negative control recording an actual non-capture/timeout
  outcome (the Police-side mirror of thief_repo's always-STAY-must-be-CAPTURED control).

## Constraints

- Depends on `T037` landing first (police strategy core) — do not stub or fabricate a
  brain implementation to unblock this task early.
- Follow `ADR-007`: this task wires police_repo's **own** Police brain into police_repo's
  own production path. It does not import or embed the Thief policy — that is `T041`'s
  separate, evaluation-only, statically-ported scope.

## Acceptance criteria

- [ ] `create_peer` returns the brain-driven engine for POLICE by default in production.
- [ ] Every received half-turn flows through the canonical apply/observe order (no direct belief-mutation bypass).
- [ ] Wire-boundary evidence normalization rejects malformed inbound data without raising.
- [ ] KPI harness evaluates every sub-game (never `any()`) with a real capturing/evading opponent and an always-STAY negative control.

## Verification

- `uv run pytest tests/unit/wire tests/integration/test_strategy_selfplay_kpi.py`
- `uv run ruff check src/police_peer/wire src/police_peer/sdk.py`
- `uv run python scripts/run_quality_gates.py`

## Handoff contract

Report files changed, tests executed, exact results, decisions, deviations, blockers,
newly discovered work.

## Result and evidence
