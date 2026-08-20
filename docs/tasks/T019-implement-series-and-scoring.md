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

`scoring.py` exposes one pure function `score_subgame(outcome:
SubGameOutcome) -> Scores` implementing exactly: CAPTURE → Police 20, Thief
5; SURVIVAL → Police 5, Thief 10; TECHNICAL_LOSS → 0/0; TAMPERED → 0/0; no
local formula exported. `series.py` exposes `build_series(sub_games) ->
SeriesTotals` enforcing exactly six sub-games, role alternation per the
OPEN-008 operational convention (three each), clean reset per sub-game,
unique config/log identities, additive tie (LEAGUE-006 adds the fixed 2),
diversity reward 10 only for a qualifying new-opponent win (LEAGUE-005).
Series-replace is implemented only as a rejected differential alternative,
never selectable for counted play. Error model: `InvalidSubGameCount`,
`RoleScheduleViolation`.

(Reviewed 2026-08-18: analyzed by deepseek-v4-pro, approved by glm-5.2; full rationale in docs/evidence/c06-prep-01/analysis.md sections 2, 3, 5.)

## Behavioral test plan

(gate note: `OPEN-008 blocks: criterion` on `series_aggregation` — add/replace are differential only)
- **unit (scoring)** — every GAME-013 row asserted directly: CAPTURE Police 20 / Thief 5; SURVIVAL Police 5 / Thief 10; TECHNICAL_LOSS 0/0; tie value 2.
- **unit (series)** — exactly six isolated sub-games, clean state reset, unique config/log identities; additive tie per the OPEN-008 convention; series-replace asserted as a rejected differential alternative.
- **boundary-adapter** — totals derive from CT-06 records only, never from recomputation.
- **integration** — the same verified sub-game list is the single source feeding both totals and the T018 report input.
- **failure** — TECHNICAL_LOSS/TAMPERED outcomes cannot be converted to clean or tie scores.
- **determinism** — the same verified list always yields the same totals.

## Handoff contract

Report files changed, tests executed, exact test results, decisions made, deviations, blockers, and newly discovered work. Include command output or artifact paths sufficient for the orchestrator to validate every acceptance criterion.

## Result and evidence
