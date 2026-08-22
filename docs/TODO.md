---
artifact: todo
id: TODO-POLICE
status: active
derived_from: PLAN-POLICE@0.4
owner: orchestrator
updated: 2026-08-16
---

# Police execution ledger

The task file is authoritative for task scope, bounded context, and evidence; this table is the compact execution index. Full gate detail lives in each task file, not here.

Two independent columns describe each task.

`Status` is the claimability state defined in `docs/spec/PRD_PLAN_TODO_AGENT_WORKFLOW.md` §6a: `ready` means every `depends_on` task is `done` and no `gates:` entry has `blocks: start`; `blocked` names the concrete dependency or gate; `done` means the orchestrator validated the evidence.

`Impl state` is the evidence-based implementation state, and never implies claimability:

| Value | Meaning |
|---|---|
| `not_started` | no implementation exists for this task's write set |
| `partial` | some of the write set exists, and at least one named acceptance criterion is demonstrably unmet |
| `implementation_present` | the write set is materially implemented on the integration branch; the acceptance audit is not complete |
| `review_pending` | implementation exists on an unmerged branch, not reviewed against the acceptance criteria and not integrated |
| `complete` | every acceptance criterion is demonstrated and the orchestrator validated the evidence |

A task is never marked `done` because code exists. `implementation_present` and `review_pending` are explicitly not completion claims.

| ID | Component | Type | Status | Impl state | Priority | Requirement | Depends on | Parallel | Claimed by | Task |
|---|---|---|---|---|---|---|---|---|---|---|
| T001 | system | governance | ready | not_started | P0 | CFG-001, CFG-004, CFG-005, REPORT-006, REPORT-009, SUB-009, SUB-010 | — | yes | — | [task](tasks/T001-resolve-official-inputs-and-match-profile.md) |
| T002 | system | foundation | ready | partial | P0 | NET-001, QR-014 | — | yes | — | [task](tasks/T002-select-runtime-dependencies-and-lock.md) |
| T003 | C01 | foundation | blocked | partial | P0 | ARCH-001, ARCH-002, ARCH-003, ARCH-009, CFG-002, CFG-003, CFG-006, CFG-007, CFG-008, QR-004, QR-006, QR-012, QR-013 | T002 | no | — | [task](tasks/T003-create-package-and-configuration-boundary.md) |
| T004 | C01 | component | blocked | implementation_present | P0 | GAME-001..GAME-014 | T003 | yes | — | [task](tasks/T004-implement-domain-rules.md) |
| T005 | C02 | component | blocked | review_pending | P0 | STRAT-002, STRAT-003, STRAT-004, STRAT-005, CFG-001, CFG-004 | T004 | yes | — | [task](tasks/T005-implement-scent-model-and-lock.md) |
| T006 | C02 | component | blocked | not_started | P0 | STRAT-001, STRAT-006 | T005 | yes | — | [task](tasks/T006-implement-belief-state.md) |
| T007 | C02 | component | blocked | not_started | P0 | ARCH-007, STRAT-007, STRAT-008, STRAT-009 | T004, T006 | yes | — | [task](tasks/T007-implement-role-strategy.md) |
| T008 | C03 | component | done | implementation_present | P0 | SEC-001, SEC-002, SEC-003, SEC-004, SEC-005, SEC-006, SEC-007 | T003 | yes | — | [task](tasks/T008-implement-integrity-core.md) |
| T009 | C03 | component | blocked | implementation_present | P0 | NET-001, NET-002, NET-003, NET-004 | T003 | yes | — | [task](tasks/T009-define-mcp-contract-and-peer-adapters.md) |
| T010 | C04 | integration | blocked | not_started | P0 | ARCH-004, ARCH-005, ARCH-006 | T004, T005, T008, T009 | yes | — | [task](tasks/T010-implement-orchestrator-state-machine.md) |
| T011 | C04 | component | blocked | not_started | P0 | ARCH-008, NET-005, CFG-007, CFG-008 | T010 | yes | — | [task](tasks/T011-implement-deadlines-retry-and-watchdog.md) |
| T012 | C03 | component | blocked | implementation_present | P1 | NET-005, SEC-002, SEC-005 | T009, T010 | yes | — | [task](tasks/T012-implement-inbound-delivery-safety.md) |
| T013 | C03 | component | blocked | not_started | P0 | SEC-008, SEC-009, LEAGUE-007, QR-018 | T008, T010 | yes | — | [task](tasks/T013-implement-step-zero-and-token-metering.md) |
| T014 | C05 | component | blocked | not_started | P0 | OBS-001, OBS-002, OBS-003, OBS-004, QR-017 | T006, T010 | yes | — | [task](tasks/T014-implement-live-gui.md) |
| T015 | C05 | component | blocked | not_started | P0 | OBS-005, OBS-006, SEC-005, SEC-006 | T008, T010, T014, T033 | yes | — | [task](tasks/T015-implement-replay-and-audit-view.md) |
| T016 | C06 | component | blocked | not_started | P0 | CFG-009, CFG-010, REPORT-005, REPORT-006, REPORT-007, REPORT-008, REPORT-009 | — | yes | — | [task](tasks/T016-adopt-official-report-artifact-schemas.md) |
| T017 | C06 | component | blocked | implementation_present | P0 | SEC-010, REPORT-001, REPORT-002, REPORT-003, REPORT-004, REPORT-010, REPORT-011, REPORT-012, REPORT-013, QR-008 | T002, T003 | yes | — | [task](tasks/T017-implement-mail-gatekeeper.md) |
| T018 | C06 | integration | blocked | implementation_present | P0 | REPORT-001, REPORT-004, REPORT-005, REPORT-006, REPORT-007, REPORT-008, REPORT-009 | T012, T013, T015, T016, T017 | no | — | [task](tasks/T018-integrate-signed-reporting.md) |
| T019 | C06 | component | blocked | implementation_present | P0 | GAME-013, LEAGUE-001, LEAGUE-005, LEAGUE-006 | T004, T010, T013 | yes | — | [task](tasks/T019-implement-series-and-scoring.md) |
| T020 | C06 | component | blocked | implementation_present | P0 | LEAGUE-002, LEAGUE-003, LEAGUE-004, LEAGUE-007 | T018, T019 | yes | — | [task](tasks/T020-implement-league-pairing-guards.md) |
| T021 | system | verification | blocked | not_started | P1 | QR-005, QR-009, QR-010, QR-011 | T004, T005, T006, T007, T008 | yes | — | [task](tasks/T021-close-unit-property-and-coverage-gaps.md) |
| T022 | system | integration | blocked | not_started | P1 | NET-001, NET-005, SEC-002, SEC-005, REPORT-009 | T011, T012, T018, T019 | yes | — | [task](tasks/T022-build-recovery-and-interoperability-tests.md) |
| T023 | system | governance | blocked | not_started | P1 | OBS-007, SUB-003, SUB-004, SUB-005, SUB-012, QR-002, QR-015, QR-017 | T014, T015, T020, T022 | no | — | [task](tasks/T023-complete-documentation-and-real-evidence.md) |
| T024 | system | verification | blocked | not_started | P1 | QR-001, QR-003, QR-004, QR-005, QR-006, QR-007, QR-010, QR-011, QR-012, QR-013, QR-014, QR-019 | T021, T022, T023 | no | — | [task](tasks/T024-run-repository-compliance-audit.md) |
| T025 | system | verification | blocked | not_started | P2 | QR-016 | T022 | yes | — | [task](tasks/T025-run-optional-excellence-study.md) |
| T026 | system | release | blocked | not_started | P0 | SUB-001, SUB-002, SUB-003, SUB-004, SUB-005, SUB-006, SUB-007, SUB-008, SUB-009, SUB-010, SUB-011 | T020, T024 | no | — | [task](tasks/T026-prepare-release-and-submission.md) |
| T027 | C02 | component | blocked | not_started | P2 | STRAT-008, SEC-009, QR-008, QR-018 | T002, T007, T013, T017 | yes | — | [task](tasks/T027-implement-optional-language-model-provider-adapter.md) |
| T028 | C01 | component | blocked | not_started | P0 | CFG-001, CFG-009 | T003 | yes | — | [task](tasks/T028-author-shared-game-contract.md) |
| T029 | C01 | verification | blocked | not_started | P1 | GAME-013, GAME-014 | T004, T028 | yes | — | [task](tasks/T029-run-stage-one-gate.md) |
| T030 | C03 | component | blocked | implementation_present | P1 | — | T010 | yes | — | [task](tasks/T030-port-fsm-alternative-driver.md) |
| T032 | C06 | component | ready | implementation_present | P0 | REPORT-005, REPORT-006, REPORT-007, REPORT-008, REPORT-009 | T002, T003 | yes | — | [task](tasks/T032-internal-reporting-artifact-contract.md) |
| T033 | C03 | component | not_started | not_started | P0 | SEC-005, SEC-006, OBS-006 | T008 | yes | — | [task](tasks/T033-replay-shape-adapter-headless-harness.md) |
| T034 | C03 | component | not_started | not_started | P0 | OBS-006, SEC-005, SEC-006 | T008 | yes | — | [task](tasks/T034-per-subgame-evidence-capture.md) |
| T046 | C06 | component | not_started | not_started | P0 | REPORT-005, REPORT-006, REPORT-007, REPORT-008, REPORT-009, OBS-006 | T033, T034 | yes | — | [task](tasks/T046-replayable-kit-artifact-emission.md) |
| T047 | C05 | component | not_started | not_started | P0 | OBS-006, OBS-007 | T033, T046 | yes | — | [task](tasks/T047-headless-replay-cli-integration.md) |
