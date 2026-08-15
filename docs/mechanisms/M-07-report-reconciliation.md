---
artifact: mechanism-prd
id: M-07
component: C06
status: draft
shared: true
owner: orchestrator
updated: 2026-08-15
---

# M-07 — Report Reconciliation & Settlement

## Why this mechanism has its own PRD

Two independently produced signed reports must reconcile into one agreed result, and two separate source contradictions/ambiguities (OPEN-004's sanction conflict, OPEN-008's tie/terminology ambiguity) both land squarely on this reconciliation step. This is a real algorithm with a genuinely contested specification, not an implementation detail of C06's PRD.

## Governing requirements

REPORT-005…009 (signed JSON report, four artifact schemas, common identifier, report content, mutual agreement and consistency); consumes GAME-013 (fixed score table) and LEAGUE-001, LEAGUE-005, LEAGUE-006 (six-sub-game series, diversity reward, tie score) from C01/C06 without redefining them.

## Specified behavior (binding)

- The final report is a uniform, signed, machine-readable JSON attachment; a plaintext report is rejected (REPORT-005).
- The four JSON artifacts are `declaration_<game_id>.json`, `config_<game_id>_g<NN>.json`, `log_<game_id>_g<NN>.json`, and `result_<game_id>.json`, carrying a common identifier (REPORT-006).
- Declaration contains teams/members, both role repositories, MCP addresses, hardware, model, token budget, and start/end times; configuration contains agreed terms; log records steps and Commit-Reveal; result summarizes sub-games and scores (REPORT-007).
- The result report includes repository links, the Git commit for each sub-game, and total LLM tokens per sub-game and series (REPORT-008).
- Both teams must agree on the result and send separate, consistent reports (REPORT-009).

## What is genuinely open

- **OPEN-004** (source contradiction): §9.3.3 says the non-reporting side receives no credit; Appendix E rule 35 says a missing/conflicting report invalidates the game and gives both sides 0. Until resolved, two consistent reports are required and automatic scoring of a conflict is refused.
- **OPEN-008** (terminology/series semantics): whether the cumulative-tie score of 2 (LEAGUE-006) replaces or adds to accumulated points, and the exact role-schedule/aggregation labels used in the report fields, are unresolved. The fixed six-sub-game count and the tie value itself are not in question — only how they aggregate and what they are called in the report.

## Reconciliation algorithm (binding shape, pending the two items above)

1. Each side independently derives its own result JSON from its locally verified audit (M-05's output) and its own series/scoring state (C06, consuming C01's GAME-013 table).
2. Before sending, each side reconciles its own draft against the received peer draft for the same `game_id`: identifiers, sub-game count, and per-sub-game scores must match.
3. A mismatch is never resolved by silently picking one side's number — it is a report-refusal case, deferred to OPEN-004's sanction once it resolves.
4. Both sides send independently; neither waits for the other's send to complete before compiling its own JSON, but does wait for the reconciliation pass in step 2.

## Compatibility decision matrix (differential tests only)

| Axis | Candidates | Selection gate |
|---|---|---|
| Missing/conflicting-report sanction | non-reporting side gets no credit · both sides get 0 | OPEN-004 |
| Tie aggregation | series-add · series-replace | OPEN-008 |
| Role-schedule labeling | per-source candidate labels | OPEN-008 |

## Acceptance scenarios

- [ ] Reconciliation correctly detects a mismatched draft between two synthetic peer results and refuses to auto-resolve it. {#reconciliation_mismatch_detection}
- [ ] The missing/conflicting-report sanction is exercised only as a differential test pending OPEN-004. {#sanction_settlement}
- [ ] Tie-aggregation candidates (add vs. replace) are exercised only as differential tests pending OPEN-008; the fixed tie value of 2 and six-sub-game count are asserted directly. {#tie_aggregation}

## Owning task

T018 (integration task, depends on T012, T013, T015, T016, T017); OPEN-004 gates `{#sanction_settlement}` and OPEN-008 gates `{#tie_aggregation}`, both `blocks: criterion`.
