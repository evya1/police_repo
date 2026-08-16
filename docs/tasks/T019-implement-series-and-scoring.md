---
id: T019
status: blocked
implementation_state: not_started
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

Series aggregation must not become a central judge; each peer derives its own result and later reconciles it with the opponent.

Every explicitly required behavior is preserved: exactly six sub-games per series, the fixed tie value of 2, and the GAME-013 score table. What the source does not fix is role assignment and alternation, and whether the tie score replaces or augments accumulated points. Those are recorded as the **series execution convention** under OPEN-008 in `docs/spec/OPEN_QUESTIONS.md`:

- roles alternate across the six sub-games starting from this peer's natural role, so each side plays each role three times;
- each sub-game runs from a clean state with its own configuration and log identity, and no state carries across sub-games;
- series totals accumulate per sub-game and the tie value is **added** to the accumulated total rather than replacing it;
- a technical-loss or tampered outcome scores zero for both sides and can never become a clean or tie outcome.

This convention governs local execution only. It is an operational convention, not an official rule, and it is never described as one. Role assignment, alternation, and tie aggregation materially affect counted scoring, so the schedule and the tie rule are confirmed against the official reporting files or a lecturer answer **before counted play**.

## Gates

- `OPEN-008` (`open`, `blocks: criterion`) — the task may be claimed and implemented now; only the acceptance criterion scoped `series_aggregation` waits.

## Constraints

- Do not edit the canonical PRD.
- Do not silently redefine the repository PLAN or task dependencies.
- Do not widen scope or treat a derived design decision as a source requirement.
- Edit only the declared write set; request an orchestrator-approved change before crossing it.
- Escalate requirement conflicts, missing official inputs, and newly discovered work.

## Acceptance criteria

- [ ] Exactly six configured sub-games run under the recorded alternation schedule, with clean state reset and unique configuration and log identities per sub-game.
- [ ] All fixed score rows match the canonical GAME-013 table, and the cumulative tie value of 2 is added to accumulated totals rather than replacing them.
- [ ] Tests distinguish series-add, series-replace, and per-sub-game tie semantics, assert the recorded convention is what executes, and keep series-replace as an explicit rejected alternative. Counted play is refused until the schedule and tie rule are confirmed against an authoritative answer. `{#series_aggregation}`
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
