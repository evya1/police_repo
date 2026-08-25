---
artifact: stage-todo
id: TODO-POLICE-STRATEGY
status: active
version: 0.1
derived_from: PLAN-POLICE-STRATEGY@0.1 · PRD-POLICE-STRATEGY@0.1
applies_to: police_repo only (role-owned)
owner: orchestrator
updated: 2026-08-22 (review remediation T044 landed — BLOCKER-1/HIGH-2/HIGH-3/MEDIUM-4/5/6/7 and LOW-11 closed; TC-P22 now measures the production composition and PASSES at 80% (16/20) against the 60% gate, superseding the earlier 35% FAIL recorded here; TC-P20/TC-P21/TC-P23 green, TC-P24 run as a normalized semantic comparison with the drift logged as T045; see the Review remediation section below. Stage opened 2026-08-21.)
---

# TODO — Police Strategy (Stage 3, role-specific part)

Task ledger for building the Police strategy from `PRD_police_strategy.md` +
`PLAN_police_strategy.md`. Order follows the PLAN §12 stub-replacement spine: shared core
first, then the pursuit + barrier policy, then the decision-path swap, then the
verification close-out. **Big-bang integration is not allowed** — the spine test
(`tests/integration/test_series_loopback.py`) must be green after every task, and no task
leaves a new strategy module unwired and untested.

## How this ledger works

- **Status values:** `not started` · `in progress` · `blocked` (names the dependency/gate) ·
  `done` (orchestrator-verified evidence only).
- **Ready rule:** a task is ready when every `depends on` task is `done` and no gate blocks
  start. Two external items gate this stage: (1) the **belief board (T006)** — its ledger
  (`TODO_belief_board.md`) must record G-B3 before PS-04 is claimed; (2) the **PLANQ-008**
  team decision (`TBD_TEAM_DECISION`) — it is `blocks: criterion` on T007's
  `{#heuristics}` acceptance criterion, **not** `blocks: start`: the stage proceeds, and
  only that criterion waits. The PRD §9 values are the approval baseline; the TC-P22
  fixtures are the seeded scenarios it reviews.
- **Responsibility:** `ORC` = orchestrator; `IA` = implementation agent (claims the mapped
  repo task per `AGENTS.md`, edits only its write set, hands off with evidence: files
  changed, tests executed, exact results, decisions, deviations, blockers, newly
  discovered work).
- **Repo mapping:** the repo task file is the claim unit: **T007** (`Implement Role
  Strategy`, write set `src/police_peer/strategy/` + `tests/unit/strategy/`); **T021**
  absorbs the property-suite + coverage close-out (`tests/property/`). Two ORC-recorded
  write-set extensions are needed before claims (workflow §4: no silent scope expansion,
  the belief stage's FR-B9 recording pattern): (a) `src/police_peer/wire/__init__.py` for
  the S3 brain swap (stage-2 glue, not in T007's write set); (b)
  `tests/integration/test_strategy_selfplay_kpi.py` for the KPI harness. **T027**
  (optional LLM provider, P2, `optional: true`) stays deferred — PLANQ-003/PLANQ-004
  `blocks: start` on that task only; its `TextProvider` seam is built by PS-02, its
  implementation is not.
- **Cross-repo rule:** the strategy **shared core** (`strategy/decision.py`,
  `strategy/base.py`, `strategy/hints.py`, `strategy/inject.py`, `strategy/__init__.py`)
  must stay mutually consistent with the thief-repo counterparts — identical content
  modulo package import path and the role constant (the shared-scent/belief rule). The
  thief-side docs are delivered (`thief_repo/docs/PRD/PLAN/TODO_thief_strategy.md`), and
  this doc's shared-core sections were written as their mirror; the shared-core **code**
  files land in each repo with that repo's own task (thief TS-02 / police PS-02), so the
  ORC code sync check (TC-P24) runs once **both** sides' files exist — until then each
  repo checks single-repo internal consistency, and the three role-justified wording
  divergences are pre-recorded in `PLAN_police_strategy.md` §5 (shared-core sync notes)
  so the sync normalizes them deliberately.
- **Progress:** the IA updates `status` (and claim fields in the repo task file) while
  working; the ORC verifies evidence before `done`.
- **Spine invariant:** `tests/integration/test_series_loopback.py` green after **every**
  task (PLAN §12 invariant).

## Stage task index

| ID | Task | Phase | Pri | Status | Owner | Depends on | Maps to (repo / PRD) | Gate |
|---|---|---|---|---|---|---|---|---|
| PS-01 | Prerequisites & entry criteria | A | P0 | done | ORC | — | T004/T005/T008/T009/T010 assumed · T006 (belief) · write-set extensions | G-P0 |
| PS-02 | Shared core: `Decision`, `BrainBase`, `HintWriter`, injection seam | B | P0 | done | IA | PS-01 | T007 · FR-P1 (partial), FR-P6, FR-P7, FR-P9, FR-P11 | G-P1 |
| PS-03 | `PoliceBrain` + `where_place_barrier`: pursuit scan, diffuse fallback, full barrier pipeline | B | P0 | done | IA | PS-02 | T007 · FR-P2, FR-P3, FR-P4, FR-P5, FR-P8 | G-P1 |
| PS-04 | Spine swap: `BrainDrivenEngine` in the glue (S3a/S3b/S3c) | C | P0 | implementation present (T044 — reachable from the CLI; G-P2 not re-audited) | IA | PS-03 (+ T006 G-B3, write-set extension recorded) | T007 · PLAN §12, SD-P5, SD-P7 | G-P2 |
| PS-05 | Verbal hardening: isolation, verdict rule, cap, lie rate | C | P0 | not started | IA | PS-03 | T007 · FR-P6, FR-P7, TC-P14…P16 | G-P2 |
| PS-06 | KPI self-play + property + determinism + perf + coverage close-out | D | P1 | in progress (TC-P22 gap CLOSED by T044 at 80%; TC-P20/P21/P23 green, coverage 93.16%) | IA | PS-04, PS-05 | T007 + T021 · PRD §2.3 KPIs, NFR-1/2 | G-P3 |
| PS-07 | Shared-core cross-repo sync + docs sync | D | P1 | in progress (T044 ran TC-P24 as a normalized semantic comparison; residual drift opened as T045; docs reconciled) | ORC | PS-06 + thief counterparts' code (thief TS-02 — code exists, ledger stale) | — · Goal 7, NFR-6 | G-P3 |

## Phase A — Prerequisites

### PS-01 — Prerequisites & entry criteria (owner: ORC)

- [x] Verify the stage entry assumptions hold on the integration branch: C01 domain +
  config (T003/T004), scent model + lock (T005), orchestrator FSM + turn loop with
  stand-in engine (T010), MCP transport + turn frames (T009), integrity core (T008).
- [x] Confirm the belief stage's G-B3 is recorded in `TODO_belief_board.md` (real
  `BeliefGrid` live in the turn handler, spine green) — the entry criterion for PS-04.
- [x] Record the two write-set extensions in `docs/tasks/` **before** claims (workflow
  §4): (a) `src/police_peer/wire/__init__.py` (S3 brain swap); (b)
  `tests/integration/test_strategy_selfplay_kpi.py` (KPI harness).
- [x] Confirm T007 is `ready` in the repo ledger (depends_on T004, T006 done) and note
  that PLANQ-008 (`TBD_TEAM_DECISION`, `blocks: criterion`) does **not** block the claim;
  the PRD §9 values are the approval baseline for it.

**Verification:** ORC checklist with branch/commit references. **DoD:** G-P0 passed.

#### Evidence (2026-08-21)

**Branch:** `police-strategy` · HEAD: `7ce031d` (Added missing PLAN, PRD and TODO of the belief board)

##### Prerequisite verification

The domain/configuration, scent model, belief board, orchestrator, MCP transport, and integrity
prerequisites are integrated and verified on `production-fixes`.

##### Write-set extensions

Both extensions recorded in `docs/tasks/` before any strategy task claim (workflow §4):

| Extension | File | Status |
|---|---|---|
| (a) `src/police_peer/wire/__init__.py` (S3 `BrainDrivenEngine` seam) | `docs/tasks/T042-extend-wire-brain-swap.md` | recorded |
| (b) `tests/integration/test_strategy_selfplay_kpi.py` (KPI harness) | `docs/tasks/T043-extend-kpi-harness.md` | recorded |

##### T007 readiness

T007 ledger: `status: blocked`, `depends_on: [T004, T006]`. T004 is `blocked`, T006 is
`blocked` → T007 is **not `ready`** in the strict ledger sense. However:

- PLANQ-008 (`TBD_TEAM_DECISION`, `blocks: criterion`) does **not** block the claim
  (only the `{#heuristics}` acceptance criterion waits).
- The PRD §9 configuration values are the approval baseline for T007's heuristics
  criterion — they are present in `config/game.json`.
- Code for T004's write set exists (`src/police_peer/domain/`); T006's write set
  (`src/police_peer/belief/`) exists with `grid.py`, `hints.py`, `probe.py`, `update.py`
  (the belief board stage is a sibling and its G-B3 gates PS-04, not PS-02/PS-03).

**Conclusion:** T007 cannot be formally `ready` until T004 and T006 are `done`, but
PLANQ-008 does not block the claim, and the PRD §9 values are the approval baseline.
PS-02/PS-03 can proceed; PS-04 waits on G-B3.

##### Spine baseline

```
uv run pytest tests/integration/test_series_loopback.py -q   # 100% passed
uv run pytest -q                                              # 100% passed (all suites green)
```

**DoD:** G-P0 passed — phase A complete, gaps documented, write-set extensions recorded.

## Phase B — Shared core and the policy

### PS-02 — Shared core: `Decision`, `BrainBase`, `HintWriter`, injection seam (owner: IA → repo task T007)

- `strategy/decision.py`: frozen `Decision` dataclass, field invariants (PRD §5.3 table).
- `strategy/base.py`: `BrainBase` — pinned two-phase `decide()` (move → hint; forced-STAY
  path with `fallback=True` and **no barrier** — pinned order), `reset(start)` (visited =
  `{start}`, `last_field = {}`), `note_evidence(field)` (SD-P5), `visited` update on
  orthogonal MOVE only (FR-P8; unconsumed by the Police policy this stage).
- `strategy/hints.py`: `HintWriter` — role-parameterized template banks (3–4 truth/lie
  variants each), seeded lie roll ≈ 0.4, verdict rule-computed (contains or
  Chebyshev-adjacent ⇒ "truth"), generic non-landmark fallback line, `_cap` to
  `hint_max_words`; `TextProvider` Protocol seam (SD-P6 — seam only, no adapter).
- `strategy/inject.py`: `resolve_brain_cls` (fail-fast `ValueError`/`TypeError`),
  `resolve_brain` (seeded construction; per-sub-game role, FR-P9).
- `strategy/__init__.py`: public re-exports.
- Unit tests TC-P01, TC-P17, TC-P19 (partial: import scan), TC-P15 (partial: phase
  order), TC-P18 (partial: `BrainBase` state behavior).
- Shared-core files written per the PLAN §5 sync notes (role-neutral docstrings) so the
  PS-07/TS-07 cross-repo sync only normalizes the three pre-recorded divergences.

**Verification:** `uv run pytest tests/unit/strategy -q` (68 passed); `uv run ruff check
src/police_peer/strategy tests/unit/strategy` (all checks passed); line cap: barriers.py 127
lines, hints.py 144 lines, all others under cap. **DoD:** G-P1 — shared core constructible
with zero model/network dependencies; the seam fail-fast behavior proven; template hints
generate offline.

#### Evidence (2026-08-21)

**Branch:** `police-strategy` · HEAD: `7ce031d`

| Artifact | Path | Lines (non-blank/non-comment) |
|---|---|---|
| `Decision` | `src/police_peer/strategy/decision.py` | 24 |
| `BrainBase` | `src/police_peer/strategy/base.py` | 84 |
| `HintWriter` + `TextProvider` | `src/police_peer/strategy/hints.py` | 144 |
| `resolve_brain_cls` / `resolve_brain` | `src/police_peer/strategy/inject.py` | 92 |
| `__init__` | `src/police_peer/strategy/__init__.py` | 25 |
| TC-P01 | `tests/unit/strategy/test_decision.py` | — |
| TC-P15 (partial) | `tests/unit/strategy/test_base.py` | — |
| TC-P17 (partial) | `tests/unit/strategy/test_hints.py` | — |
| TC-P18 (partial) | `tests/unit/strategy/test_base.py` | — |
| TC-P19 (partial) | `tests/unit/strategy/test_purity.py` | — |

Shared-core sync notes: docstrings are role-neutral (per PLAN §5 sync notes); the three
pre-recorded divergences are: (1) `note_evidence` docstring references "the role's
diffuse-fallback input" (role-neutral); (2) forced-STAY comment says "forced STAY; no
barrier (pinned order)" (role-neutral); (3) `resolve_brain_cls` default-brain line says
"police_repo: PoliceBrain" (role constant).

### PS-03 — `PoliceBrain` + `where_place_barrier`: pursuit scan, diffuse fallback, full barrier pipeline (owner: IA → repo task T007)

- `strategy/barriers.py`: **`where_place_barrier`** (PRD FR-P2 pipeline: guards → peak →
  per-candidate mass/cut → no-value / self-route / reserve skips → threshold; strictly-
  greater first-candidate tie) + `cut_value` (BFS region collapse; `c == peak ⇒ cut =
  before`) + `_reachable` (flood-fill helper) — pure functions, no engine mutation.
- `strategy/police.py`: `PoliceBrain` — `_target` (FR-P3 chain: peak above
  `min_confidence` → `hottest(last_field)` → board centre), `_decide_move` (**barrier
  first**: `where_place_barrier` → `("STAY", target)`; else the pursuit scan — first
  minimum of `(manhattan(dest, threat), -belief.prob(dest))` in CT-01 order, `(action,
  None)`), weights from the `[strategy.police]` config mapping (PRD §9).
- Unit tests TC-P02 (unit level), TC-P03 (all four pursuit branches, boundary included),
  TC-P04, TC-P05, TC-P06, TC-P07, TC-P08, TC-P09, TC-P10, TC-P11, TC-P12, TC-P13,
  TC-P18 full; A/B fixtures for MS-3 (swapped belief peak vs. uniform belief ⇒ different
  actions in the pursuit fixtures).

**Verification:** `uv run pytest tests/unit/strategy -q` (68 passed); `uv run ruff check
src/police_peer/strategy tests/unit/strategy` (all checks passed); line cap: barriers.py 127
lines, police.py 112 lines, all others under cap. **DoD:** G-P1 complete — the policy is
deterministic and legal by construction; `where_place_barrier` is unit-green step by step
(guards, value, self-route, reserve, threshold, tie); belief demonstrably changes selection
(MS-2/MS-3 fixtures).

#### Evidence (2026-08-21)

**Branch:** `police-strategy` · HEAD: `7ce031d`

| Artifact | Path | Lines (non-blank/non-comment) |
|---|---|---|
| `where_place_barrier` + `cut_value` + `_reachable` | `src/police_peer/strategy/barriers.py` | 127 |
| `PoliceBrain` | `src/police_peer/strategy/police.py` | 112 |
| TC-P02 (unit) | `tests/unit/strategy/test_police.py` | — |
| TC-P03 (4 branches) | `tests/unit/strategy/test_police.py` | — |
| TC-P04 (commit to peak) | `tests/unit/strategy/test_police.py` | — |
| TC-P05 (tie-break) | `tests/unit/strategy/test_police.py` | — |
| TC-P06 (forced STAY) | `tests/unit/strategy/test_police.py` | — |
| TC-P07 (guards) | `tests/unit/strategy/test_barriers.py` | — |
| TC-P08 (value) | `tests/unit/strategy/test_barriers.py` | — |
| TC-P09 (self-route) | `tests/unit/strategy/test_barriers.py` | — |
| TC-P10 (reserve) | `tests/unit/strategy/test_barriers.py` | — |
| TC-P11 (threshold/tie) | `tests/unit/strategy/test_barriers.py` | — |
| TC-P18 full | `tests/unit/strategy/test_base.py` | — |

A/B fixtures: `_UniformBelief` vs `_PeakBelief` in `test_police.py` — swapped belief peak
vs. uniform belief produces different actions in the pursuit fixtures (TC-P03).

## Phase C — The loop and the verbal layer

### PS-04 — Spine swap: `BrainDrivenEngine` in the glue (owner: IA → repo task T007, write-set extension recorded)

- `src/police_peer/wire/__init__.py`: `BrainDrivenEngine` implementing the existing
  `TurnEngine` seam (PLAN §12 S3a): fresh `GameEngine` per sub-game (C01, as today);
  POLICE sub-games: `resolve_brain(config, role)` + `brain.decide(state, belief,
  opponent_hint, arena)` + when `barrier_cell` is set: `engine.place_own_barrier
  (barrier_cell)` then `engine.apply_own_move(action)` + the outgoing frame's
  `barrier_placed` field (GAME-012 same-turn declaration); THIEF sub-games: the stand-in
  selection is kept on the existing path, labeled (SD-P7).
- S3b: the outgoing frame's hint comes from `Decision.hint` (template writer), replacing
  the canned `"I am here"`.
- S3c: `brain.note_evidence(smell_grid)` on each received turn, before the decision
  (SD-P5).
- Spine run with the real belief (belief stage S1/S2 already wired) and the real Police
  brain; TC-P23.

#### Evidence (2026-08-21)

- `BrainDrivenEngine` implemented in `src/police_peer/wire/__init__.py`, subclassing
  `StandInEngine`.
- POLICE sub-games: brain resolved via `resolve_brain(config, role)`, belief via
  `build_belief`, `brain.decide()` produces the move + barrier + hint.
- Barrier placement: `engine.place_own_barrier(barrier_cell)` called before
  `engine.apply_own_move(action)` when `barrier_cell` is set; `barrier_placed` added
  to the outgoing frame.
- THIEF sub-games: stand-in path preserved (SD-P7).
- Integration tests updated to use `BrainDrivenEngine` for police on all four spine
  tests (`test_series_loopback`, `test_playable_lifecycle`, `test_series_fault_audit`,
  `test_local_mcp_smoke`).

**Verification:** `uv run pytest tests/integration/test_series_loopback.py -q` green with
the real brain on Police sub-games; `uv run pytest tests/unit/strategy -q`; ruff; line
cap. **DoD:** G-P2 — the decision path is brain-driven end-to-end over loopback, full
six-sub-game series settles, no stand-in decision left on the Police path, every placed
barrier declared on the wire in the same turn.

- All 408 tests green.
- `uv run ruff check` clean on all changed files.

### PS-05 — Verbal hardening: isolation, verdict rule, cap, lie rate (owner: IA → repo task T007)

- TC-P14 full (word cap, landmark naming, verdict domain, seeded lie fraction
  0.30–0.50 over 1000 hints, deterministic per seed).
- TC-P15 full (boom hint writer / boom provider never change the action **or barrier**;
  a slow or failed provider ⇒ template fallback with the action unchanged — CT-02 failure
  behavior; NG-003: no consultation on the move path).
- TC-P16 (verdict recomputed independently from position + asserted landmark region ⇒
  matches the sealed verdict on every generated hint).

#### Evidence (2026-08-21)

- TC-P14 fully covered: existing tests pass (word cap, landmark naming, verdict domain,
  seeded lie fraction 0.30–0.50, deterministic per seed).
- TC-P15 full: added `test_provider_failure_does_not_affect_action_or_barrier` and
  `test_slow_provider_does_not_affect_action_or_barrier` in `tests/unit/strategy/test_hints.py`.
  These verify that a boom or slow provider cannot influence the hint output and that
  the template fallback path is reached without side effects.
- TC-P16 fully covered: existing tests pass (verdict recomputed independently, generic
  fallback truth).

**Verification:** `uv run pytest tests/unit/strategy -q`; spine still green; ruff; line
cap. **DoD:** G-P2 complete — the verbal layer is bounded, isolated, and audit-consistent
(M-03 `{#hint_isolation}` proven).

- All 408 tests green.
- `uv run ruff check` clean on all changed files.

## Phase D — Verification close-out

### PS-06 — KPI self-play + property + determinism + perf + coverage close-out (owner: IA → repo task T007 + T021, write-set extension recorded)

- `tests/property/strategy/` (T021 write set): TC-P02 full — 10k random seeded
  (engine, belief, field) fixtures ⇒ action in the legal set; `barrier_cell` `None` or a
  legal candidate with `action == "STAY"` and quota respected; `fallback` flag exact.
- `tests/integration/test_strategy_selfplay_kpi.py` (extension recorded in PS-01):
  TC-P22 — 20 seeded games, role-pinned Police sub-games, shipped config: capture rate
  within 35 rounds vs the reference `ThiefBrain` test double ≥ 60%; median
  rounds-to-capture ≤ 28; captures using ≤ 8 barriers ≥ 50%. The reference baseline brain
  lives in the harness as a test double (registered evidence, non-authoritative).
- Determinism TC-P20 (two runs, same seed + same wire transcript ⇒ byte-identical
  decision logs); perf TC-P21 (≤ 10 ms p99 over 10k iterations, **including
  `where_place_barrier`**).
- Coverage to ≥ 85% on `strategy/`; docs sync: M-03 cross-link to the stage docs, C02
  PLAN note, stage-3 index in `docs/` (orchestrator).

#### Evidence (2026-08-22)

**Branch:** `police-strategy` · HEAD: `1cdfefc`

**Done (IA-verified; ORC review pending):**

| Item | Result |
|---|---|
| TC-P02 full — 10k random-seeded fixtures (`tests/property/strategy/test_tc_p02.py`, 4 tests; T021 write set) | green |
| TC-P23 spine (`tests/integration/test_series_loopback.py`, 3 tests) | green (combined run: 7 passed) |
| KPI harness: `tests/integration/test_strategy_selfplay_kpi.py` (reference `RandomThiefEngine` test double, `KPIResult`, shipped `_terms`) + runner `test_strategy_selfplay_kpi_harness.py` (TC-P22/P20/P21) | in tree |
| TC-P20 determinism (two 20-game runs, same seed ⇒ identical rows) | pass |
| TC-P21 perf (≤ 10 ms p99 over 10k `where_place_barrier` iterations) | pass |
| Coverage on `strategy/` ≥ 85% | met — `barriers.py` 98%, `base.py` 97%, `hints.py` 98%, `police.py` 98%, `baseline.py` 60% (stand-in, non-policy), `decision.py` / `inject.py` / `__init__.py` 100% |

**Gaps (documented, not done):**

- **TC-P22 KPI self-play — FAIL:** capture rate **35% (7/20)** vs the ≥ 60% requirement (seed 7,
  20 role-pinned Police games, shipped config, reference `RandomThiefEngine` double). The two
  remaining sub-KPI asserts (median rounds-to-capture ≤ 28; ≥ 50% of captures using ≤ 8
  barriers) were not reached — the test aborts on the first assert. KPI numbers are therefore
  **not recorded** (G-P3 DoD item open); closing requires a policy fix or an ORC-approved
  threshold review.
- **Docs-sync items — not done:** M-03 cross-link to the stage docs, C02 PLAN note, stage-3 index
  in `docs/` (orchestrator) — none present (grep of `police_repo/docs/` finds no references).
- **Repo-wide coverage gate:** pyproject `fail_under = 85` (whole repo) fails on strategy-scoped
  runs (32.65% on the unit + property + KPI + loopback set) — outside this stage's DoD
  (`strategy/`-scoped, met); a T021-scope blocker.
- **Deviation (write set + verification command):** PLAN §15 runs
  `tests/integration/test_strategy_selfplay_kpi.py`, which holds only the harness (0 tests
  collected); the executable TC-P22/P20/P21 tests live in `test_strategy_selfplay_kpi_harness.py`.
  Write-set extension (b) (PS-01) covers only `test_strategy_selfplay_kpi.py` — the runner file
  was created outside the recorded extension; ORC reconciliation needed.

**Verification:** full command set of PLAN §15 in the police repo; ORC evidence review.
**DoD:** G-P3 close-out candidate — KPI numbers recorded, property suite green,
determinism/latency inside budget.

### PS-07 — Shared-core cross-repo sync + docs sync (owner: ORC)

- Once the thief counterparts' code exists (thief ledger TS-02 in `thief_repo`): the ORC
  sync-checks `strategy/{decision,base,hints,inject,__init__}.py` — identical content
  modulo package import path and the role constant (the cross-repo rule); the three
  role-justified wording divergences pre-recorded in `PLAN_police_strategy.md` §5
  (shared-core sync notes) are normalized deliberately, not flagged as drift; TC-P24.
- Confirm the "shared core" sections of `PRD/PLAN/TODO_police_strategy.md` and their
  thief mirrors are mutually consistent (same schema, same invariants, same wording
  modulo role words); record G-P3 evidence; reconcile T007/T021 state in
  `docs/TODO.md`.

#### Evidence (2026-08-22)

**Branch:** `police-strategy` · HEAD: `1cdfefc` · **Status: not done — blocked on PS-06
(TC-P22 gap).**

- **Thief counterparts' code — exists (gate cleared on the code side):**
  `thief_repo/src/thief_peer/strategy/{decision,base,hints,inject,__init__}.py` + role-specific
  `thief.py`, `scoring.py`, `baseline.py`. The thief ledger
  `thief_repo/docs/TODO_thief_strategy.md` still shows TS-02…TS-07 as `not started` — stale
  relative to the in-tree code; ORC should reconcile both ledgers.
- **TC-P24 sync check — not run / not recorded.** Preliminary normalized diff (2026-08-22; police
  content with `police_peer` → `thief_peer` substituted, vs the thief files) shows drift beyond
  the import path + role constant and beyond the three pre-recorded wording divergences
  (PLAN §5 sync notes):

  | File | Unified diff | Drift observed |
  |---|---|---|
  | `decision.py` | 10 lines | mirror-reference docstring only (each file names the other repo) |
  | `base.py` | ~97 lines | mechanism ref M-03 (police) vs M-04 (thief) for the same `{#hint_isolation}` anchor; police class docstring expanded |
  | `hints.py` | ~89 lines | per-role template banks (POLICE vs THIEF phrasing) |
  | `inject.py` | ~117 lines | `ThiefBrain` import; default-brain lines (SD-P7 vs SD-T7); role-specific default |
  | `__init__.py` | ~34 lines | exports (police adds `where_place_barrier` + `PoliceBrain`; thief adds `ThiefBrain`) |

  The pre-recorded divergence list (PLAN §5) is incomplete against the actual drift — closing
  PS-07 needs deliberate ORC normalization decisions, not just a mechanical check.
**Verification:** sync check output + ORC evidence review in both repos. **DoD:** G-P3
passed — stage done.

## TC coverage progression

| After | Unit | Property | Integration (spine) | KPI/Perf/Determinism |
|---|---|---|---|---|
| PS-02 | TC-P01, P15(p), P17, P18(p), P19(p) | — | baseline green | — |
| PS-03 | + TC-P02 (unit), P03, P04, P05, P06, P07, P08, P09, P10, P11, P12, P13, P18 full | — | green | — |
| PS-04 | + TC-P23 | — | S3a/S3b/S3c wired, green | — |
| PS-05 | + TC-P14, P15, P16 full | — | green | — |
| PS-06 | all | TC-P02 full (10k) | green | TC-P20, P21, P22 |
| PS-07 | — | — | green | TC-P24 (sync check) |

## Stage definition of done (G-P3)

- [ ] MS-1…MS-5 of PRD §2.2 each have recorded evidence (test names + results).
- [ ] All TC-P## pass in the police repository; coverage ≥ 85% on `strategy/`; ruff
  clean; no file over the 150-line cap; no new dependencies; no secrets.
- [ ] Spine green with the real `PoliceBrain` on the Police decision path; opposite-role
  sub-games on the stand-in with SD-P7 recorded (full six-sub-game series settles); every
  placed barrier declared open + exact in the same turn (GAME-012).
- [ ] KPI numbers recorded from 20 seeded games: ≥ 60% capture rate within 35 rounds vs
  the reference `ThiefBrain`; median rounds-to-capture ≤ 28; ≥ 50% captures using ≤ 8
  barriers.
- [ ] PLANQ-008 baseline values (PRD §9) flagged for the team decision; the
  `{#heuristics}` criterion is checkable once approved (not blocked meanwhile).
- [ ] Shared core internally consistent, role-parameterized only by import path / role
  constant (role-neutral shared docstrings per PLAN §5 sync notes); cross-repo sync check
  recorded as pending until the thief counterparts' code exists (PS-07 owns it).
- [ ] Orchestrator has reconciled T007/T021 state in `docs/TODO.md` and recorded the G-P3
  evidence in the task files.

## Relationship to the Repository Documents

- **Upstream:** `docs/PRD_police_strategy.md` + `docs/PLAN_police_strategy.md` (this
  stage's PRD/PLAN — the TC/SD/MS IDs in this ledger are theirs); M-03 (the binding
  mechanism contract); T007 (the claim unit; PLANQ-008 `blocks: criterion` on
  `{#heuristics}`, not a start blocker).
- **Siblings (same stage, separate files):** the belief trio
  (`docs/PRD_belief_board.md` + `PLAN` + `TODO`) — T006's G-B3 is the entry criterion
  for PS-04; the delivered thief trio (`thief_repo/docs/`) — the counterpart of the
  shared-core sync check (PS-07) and the owner of the evasion policy.
- **Execution:** this ledger's tasks map to T007 (claim unit; write-set extensions for
  the glue swap and the KPI harness are ORC-recorded in PS-01) + T021 (property/coverage
  close-out); T027 stays deferred and gated (PLANQ-003/PLANQ-004). The global
  `docs/TODO.md` is reconciled by the orchestrator after each wave; this ledger does not
  edit it.
- **Assumed delivered (stage entry criteria):** C01 domain + config (T003/T004), scent
  model + lock (T005), orchestrator FSM + turn loop (T010), MCP transport + turn frames
  (T009), integrity core (T008).

## Review remediation (independent review, 2026-08-22) — T044

Recorded by the orchestrator **after** the code evidence was final. Code SHAs on
`claude/police-thief-review-remediation-v0k8tg`, branched from `police-strategy@697855b`:

| Step | SHA | What it closed |
|---|---|---|
| P1 | `7cd15fba179e24ab8735f623a586fa4399b06a48` | BLOCKER-1, HIGH-3, MEDIUM-6, LOW-11 |
| P2 | `85f943f38325f37cc1a981f1fc6ff2a68eebf821` | HIGH-2 (byte-for-byte port from `thief_repo@429b8d6`), MEDIUM-4 |
| P3 | `9fc8a78aa170af946e203c880f1429e3e48461b4` | MEDIUM-5, MEDIUM-7, TC-P24 comparison |
| Boundary | `4aaf9d74c5898733b1359996b5ca433289f773ad` | sub-game boundary leak (byte-for-byte port from `thief_repo@a5c9e06`), found by the real two-process run once captures became reachable |

Measured evidence at branch head `38bbed2` — the last commit of the wave, after the boundary fix `4aaf9d7` (an earlier draft of this paragraph cited `9fc8a78`, which predates that commit):

- `uv run pytest -q` — exit 0, **coverage 93.16%** against the enforced 85% floor.
- `uv run ruff check .` — clean. `uv run python scripts/run_quality_gates.py` — all 7 gates pass.
- **TC-P22, production-composed** (`create_peer` + shipped `config/game.json`, 20 seeded
  role-pinned games, seed 7): **16/20 captures = 80%** against the unchanged 60% gate; median
  rounds-to-capture **10.5** (gate <= 28); **16/16** captures used <= 8 barriers (gate >= 50%).
  This supersedes the 35% FAIL recorded earlier in this ledger, which measured a
  hand-assembled `BrainDrivenEngine(..., config={})` rather than the shipped composition.
  The earlier P1 measurement of 17/20 was taken before MEDIUM-7; the hint writer shares the
  brain's RNG, so hinting from the post-move cell shifts the stream and the seeded ledger.
- **TC-P20** determinism: two 20-game runs at seed 99 produce identical rows.
- **TC-P21**, three serial runs of the uninstrumented child probe (1k warm-up, 10k measured):
  p99 **1.179 / 0.967 / 1.021 ms** against the unchanged 10 ms bar; the probe reports
  `traced=False` and `coverage_imported=False`, and repository coverage stays enforced.
- `rg -n 'src\.police_peer' tests` — no matches.
- `common/` is byte-identical to `thief_repo` (identical git blob hashes for every tracked
  path under `common/`).

Scope explicitly **not** touched: production termination semantics, group scoring, reporting,
GUI, branch hygiene. **ADR-007 is unchanged and `T041` remains evaluation-only.**

### TC-P24 outcome

Run as a normalized semantic comparison (package path, role constant, role words and
requirement-ID prefixes normalized), not a byte diff and not a copy. `decision.py` and
`base.py` now agree behaviourally; `police.py` / `barriers.py` are declared role-specific in
PLAN section 5.5; the three wording divergences pre-recorded in PLAN section 5 are unchanged.
Three real drifts in `hints.py` / `inject.py` where `thief_repo` already carries the corrected
behaviour are opened as **T045** rather than absorbed into T044's write set. No Thief weights
were copied and no Police barrier behaviour was erased.

### Reconciled documents

- `docs/PLAN_police_strategy.md` section 5.2 step 4 said `hint_writer.say(state.position, ...)`;
  the shipped code now hints from the post-move destination.
- `docs/tasks/T038-w4-police-production-integration.md` referenced two non-existent task
  files (`T007-extend-wire-brain-swap`, `T007-extend-kpi-harness`); the real records are
  `T042` and `T043`.
