---
id: T041
status: blocked
priority: P2
task_type: component
component: C02
optional: true
implements: []
context_files:
  - docs/decisions/ADR-007-cross-role-strategy-port.md
read_set: []
depends_on:
  - T038
gates:
  - id: SIBLING-W3-LANDED
    kind: cross-repo
    scope: thief_repo T037/T038
    blocks: start
parallel_safe: true
claimed_by:
claim_expires_at:
write_set:
  - src/police_peer/opponents/reference_thief.py
  - tests/integration/test_strategy_selfplay_kpi.py
risk: low
---

# T041 — Cross-Role Static Port: Reference Thief Opponent (police_repo)

Per `ADR-007`. Ports a point-in-time, statically-reviewed copy of `thief_repo`'s accepted
Thief strategy (already substantially landed via `evya1/thief_repo#36`, plus `T037`'s
negative-control close-out) into `police_repo`, for KPI/self-play evaluation only.

## Constraints

- Cannot start until `thief_repo`'s `T037` (strategy-core gap closure) is accepted — the
  production-integration half (`T038` there) is already satisfied by PR #36, so this task's
  gate is effectively `T037`'s completion.
- The ported file carries a header comment recording: source repo, source commit SHA
  (expected: the `thief_repo` `T037` result commit, downstream of PR #36's `5c300bb`), port
  date, and "evaluation-only — do not wire into `sdk.py`".
- No runtime cross-repo import, no shared live module.

## Acceptance criteria

- [ ] `src/police_peer/opponents/reference_thief.py` exists with correct provenance header.
- [ ] It is exercised only from KPI/self-play test paths, never from `sdk.py`.
- [ ] A later re-port is a separate, reviewed change (not silent drift).

## Verification

- `uv run pytest tests/integration/test_strategy_selfplay_kpi.py`
- Manual review confirms no import of this module from `src/police_peer/sdk.py` or `wire/`.

## Handoff contract

Report files changed, tests executed, exact results, source SHA ported, decisions, blockers.

## Result and evidence
