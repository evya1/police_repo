---
id: T019
status: blocked
priority: P0
task_type: component
component: C06
optional: false
implements:
  - GAME-013
  - LEAGUE-001
  - LEAGUE-005
  - LEAGUE-006
context_files:
  - docs/components/C06-reporting-league/PRD.md
  - docs/components/C06-reporting-league/PLAN.md
read_set: []
depends_on:
  - T004
  - T010
  - T013
gates:
  - id: OPEN-008
    kind: open
    scope: series_aggregation
    blocks: criterion
parallel_safe: true
claimed_by:
claim_expires_at:
write_set:
  - src/police_peer/league/series.py
  - src/police_peer/league/scoring.py
  - tests/unit/league/test_series.py
  - tests/unit/league/test_scoring.py
risk: high
---

# T019 — Implement Series And Scoring

## Expected outcome

A counted series executes exactly six isolated sub-games and derives capture, survival, tie, technical-loss, and diversity scores from verified outcomes.

## Requirements implemented

- `GAME-013`
- `LEAGUE-001`
- `LEAGUE-005`
- `LEAGUE-006`

## Relevant context

Series aggregation must not become a central judge; each peer derives its own result and later reconciles it with the opponent. OPEN-008 must settle role assignment/alternation and whether the fixed tie score replaces or augments accumulated points. Series-add, series-replace, and per-sub-game behavior are differential cases only; none is authority for a production choice.

## Gates

- `OPEN-008` (`open`, `blocks: criterion`) — the task may be claimed and implemented now; only the acceptance criterion scoped `series_aggregation` waits.

## Constraints

- Do not edit the canonical PRD.
- Do not silently redefine the repository PLAN or task dependencies.
- Do not widen scope or treat a derived design decision as a source requirement.
- Edit only the declared write set; request an orchestrator-approved change before crossing it.
- Escalate requirement conflicts, missing official inputs, and newly discovered work.

## Acceptance criteria

- [ ] Exactly six configured sub-games run under the lecturer-approved role schedule, with clean state reset and unique config/log identities.
- [ ] All fixed score rows and the approved cumulative-tie application match the canonical table and OPEN-008 resolution.
- [ ] Tests distinguish series-add, series-replace, and per-sub-game tie semantics and prove that only the approved OPEN-008 profile is selectable for counted play. `{#series_aggregation}`
- [ ] Diversity reward applies only to a qualifying new-opponent win.
- [ ] Technical-loss/tamper outcomes cannot be converted to clean scores.
- [ ] The same verified sub-game list is the single source for totals and report input.

## Verification

- `uv run pytest tests/unit/league/test_series.py tests/unit/league/test_scoring.py`
- `uv run ruff check src/police_peer/league tests/unit/league`

## Implementation plan

To be completed immediately before execution.

## Handoff contract

Report files changed, tests executed, exact test results, decisions made, deviations, blockers, and newly discovered work. Include command output or artifact paths sufficient for the orchestrator to validate every acceptance criterion.

## Result and evidence
