---
artifact: stage-todo
id: TODO-BELIEF-BOARD
status: active
version: 0.1
derived_from: PLAN-BELIEF-BOARD@0.1 · PRD-BELIEF-BOARD@0.1
applies_to: police_repo + thief_repo
owner: orchestrator
updated: 2026-08-20 (stage opened; prerequisites assumed delivered per stage entry criteria — base board C01, scent model+lock T005, orchestrator FSM T010, MCP transport T009, integrity core T008)
---

# TODO — Belief Board (Stage 3, shared part)

Task ledger for building the shared belief board from `PRD_belief_board.md` +
`PLAN_belief_board.md`. Order follows the PLAN §12 stub-replacement spine: invariants
first, then the turn-loop wiring, then the hint channel, then the verification close-out.
**Big-bang integration is not allowed** — the spine test
(`tests/integration/test_series_loopback.py`) must be green after every task, and no task
builds a belief module without wiring it into the turn loop in the same or the next task.

## How this ledger works

- **Status values:** `not started` · `in progress` · `blocked` (names the dependency/gate) ·
  `done` (orchestrator-verified evidence only).
- **Ready rule:** a task is ready when every `depends on` task is `done` and no gate blocks
  start. The FR-B9 scent seam (BB-03's prerequisite) is the only external dependency; the
  orchestrator records it against T005 (extension) or a small follow-on task before BB-03
  starts — workflow §4 forbids silent scope expansion.
- **Responsibility:** `ORC` = orchestrator; `IA` = implementation agent (claims the mapped
  repo task per `AGENTS.md`, edits only its write set, hands off with evidence: files
  changed, tests executed, exact results, decisions, deviations, blockers, newly
  discovered work).
- **Repo mapping:** the repo task file is the claim unit: **T006** (`Implement Belief
  State`, write set `src/<role>_peer/belief/` + `tests/unit/belief/`) in each role
  repository; **T021** absorbs the property-suite close-out. Each BB task names the repo
  task(s) it executes. The orchestrator reconciles the repo `TODO.md` after every wave.
- **Cross-repo rule:** the belief board is shared code — after every wave that touches
  `belief/*.py`, the ORC verifies the shared-file sync (identical content in both role
  packages modulo package import path) before marking the wave integrated.
- **Progress:** the IA updates `status` (and claim fields in the repo task file) while
  working; the ORC verifies evidence before `done`.
- **Spine invariant:** `tests/integration/test_series_loopback.py` green after **every**
  task (PLAN §12 invariant).

## Stage task index

| ID | Task | Phase | Pri | Status | Owner | Depends on | Maps to (repo / PRD) | Gate |
|---|---|---|---|---|---|---|---|---|
| BB-01 | Prerequisites & entry criteria | A | P0 | not started | ORC | — | T004/T005/T008/T009/T010 assumed · FR-B9 | G-B0 |
| BB-02 | BeliefGrid core + invariants | A | P0 | not started | IA | BB-01 | T006 · FR-B1, FR-B4, FR-B6, FR-B8 | G-B1 |
| BB-03 | Scent observation: trust_v1 + kernel_bayes_v1 + emission seam | B | P0 | not started | IA | BB-02 (+ FR-B9 seam) | T006 · FR-B2, FR-B9, FR-B10 | G-B1 |
| BB-04 | Diffusion + fixed half-turn order + turn-loop wiring (S1/S2) | B | P0 | not started | IA | BB-03 | T006 · FR-B3, PLAN §12 | G-B2 |
| BB-05 | Hint channel + shared landmark registry | C | P0 | not started | IA | BB-04 | T006 · FR-B5, SD-B3 | G-B2 |
| BB-06 | Property/differential/perf/determinism suites + docs sync | C | P0 | not started | IA | BB-05 | T006 + T021 · NFR-1…NFR-3 | G-B3 |

## Phase A — Prerequisites

### BB-01 — Prerequisites & entry criteria (owner: ORC)

- [ ] Verify the stage entry assumptions hold on the integration branch: C01 domain +
  config (T004/T003), scent model + lock (T005), orchestrator FSM + turn loop with stand-in
  belief (T010), MCP transport + turn frames (T009), integrity core (T008).
- [ ] Record the FR-B9 emission-probe seam: extension of T005 (the scent module implements
  `EmissionProbe.field_at` per profile) or a small follow-on task — decision recorded in
  `docs/tasks/` before BB-03 is claimed.
- [ ] Confirm T006 is `ready` in both repos' ledgers (depends_on T005 done).
- [ ] Confirm `tests/integration/test_series_loopback.py` is green (the spine baseline).

**Verification:** ORC checklist with branch/commit references. **DoD:** G-B0 passed.

## Phase B — Core board and the turn loop

### BB-02 — BeliefGrid core + invariants (owner: IA → repo task T006)

- `belief/grid.py`: `BeliefGrid` (init uniform over legal cells, `prob`, `most_likely` with
  lexicographic tie-break, `top_k`, `peak_probability`, `exclude`, `as_matrix` deep copy,
  `_normalize` with uniform reset on degenerate total).
- `belief/__init__.py`: `build_belief(board, cfg, probe)` — private-key reads only,
  fail-fast on unknown `update_form`.
- Unit tests TC-B01…B04, TC-B12 (partial), TC-B16.

**Verification:** `uv run pytest tests/unit/belief -q`; `uv run ruff check src/<role>_peer/belief
tests/unit/belief`; line cap check. **DoD:** G-B1 — invariants 1–3 demonstrated (TC-B02
property may finish in BB-06; unit-level normalization + exclusion must pass here).

### BB-03 — Scent observation: both forms + emission seam (owner: IA → repo task T006)

- `belief/probe.py`: `EmissionProbe` Protocol + `kernel_factors`.
- `belief/update.py`: `observe_trust`, `observe_kernel`.
- Scent-side seam (per BB-01's recording): `field_at` per profile in the delivered scent
  module — additive, profile code unchanged otherwise.
- Unit tests TC-B05, TC-B07, TC-B08 (incl. the static no-profile-import scan);
  differential TC-B06 (reference worked example, `trust_v1` byte-match).

**Verification:** `uv run pytest tests/unit/belief -q` incl. `test_differential.py`; ruff;
line cap. **DoD:** G-B1 complete — both forms calibrated; seam proven in both repos.

### BB-04 — Diffusion + fixed half-turn order + turn-loop wiring (owner: IA → repo task T006)

- `belief/update.py`: `diffuse` (neighbourhood from the C01 `Board` move set — self + 4
  orthogonal in-bounds), `apply_half_turn` (the pinned order, PRD §8.1).
- Turn-loop wiring (PLAN §12 S1/S2): replace the stand-in belief in the role glue's turn
  handler with `apply_half_turn`; decision path reads real snapshot fields.
- Unit tests TC-B09 (neighbourhood, corners, no diagonals); spine run.

**Verification:** `uv run pytest tests/integration/test_series_loopback.py -q` green with
the real board; `uv run pytest tests/unit/belief -q`; ruff; line cap. **DoD:** G-B2 — real
board live in the turn loop, spine green, barrier exclusion within the same half-turn
(covered by the integration assertion or a focused unit test).

## Phase C — Hint channel and close-out

### BB-05 — Hint channel + shared landmark registry (owner: IA → repo task T006)

- `belief/hints.py`: `LANDMARK_CELLS` (New York table + `GENERIC_FALLBACK` compass words),
  `parse_landmarks` (pure, case-insensitive substring), `apply_hint` (w(0)=1, w(1)=0.5,
  reliability-weighted, renormalize).
- `BeliefGrid.apply_hint` delegation; `apply_half_turn` already orders it (BB-04) — no
  reordering.
- Sync the table to both role repositories (cross-repo rule) and to the strategy hint
  generator's import point (role PLAN step — the import is added by the role strategy task,
  this task only guarantees the table exists and is identical).
- Unit tests TC-B10, TC-B11.

**Verification:** `uv run pytest tests/unit/belief -q`; sync check; ruff; line cap.
**DoD:** G-B2 complete — hint channel deterministic, table identical in both repos.

### BB-06 — Property/differential/perf/determinism suites + docs sync (owner: IA → repo task T006 + T021)

- Property suite (TC-B02 full: 10k random update sequences, invariants after every step).
- Determinism TC-B13 (two runs, byte-identical snapshots); perf TC-B14 (both forms, 10k
  iterations, ≤ 5 ms p99).
- A/B TC-B15 (belief on/off changes ≥ 50% of fixture actions; peak-following in pursuit
  fixtures) — the fixtures are plain (belief, legal-set) pairs; no strategy code required.
- Coverage to ≥ 85% on `belief/`; docs sync: M-02 mechanism PRD cross-links, C02 PLAN
  note, stage-3 index in `docs/` (orchestrator).

**Verification:** full command set of PLAN §15 in both repos; ORC evidence review.
**DoD:** G-B3 — stage done: MB-1…MB-5 evidence recorded, both repos' ledgers reconciled,
shared-file sync check green.

## TC coverage progression

| After | Unit | Property | Differential | Integration (spine) | Perf/Determinism |
|---|---|---|---|---|---|
| BB-02 | TC-B01…B04, B12(p), B16 | — | — | baseline green | — |
| BB-03 | + TC-B05, B07, B08 | — | TC-B06 | green | — |
| BB-04 | + TC-B09 | — | — | S1/S2 wired, green | — |
| BB-05 | + TC-B10, B11 | — | — | green | — |
| BB-06 | all | TC-B02 full | all | green | TC-B13, B14, B15 |

## Stage definition of done (G-B3)

- [ ] MB-1…MB-5 of PRD §2.2 each have recorded evidence (test names + results).
- [ ] All TC-B## pass in **both** repositories; coverage ≥ 85% on `belief/`.
- [ ] Shared-file sync check green: `belief/*.py` identical across role packages modulo
      package import path; landmark table byte-identical.
- [ ] Spine test green with the real board in the turn loop (no stand-in belief left).
- [ ] FR-B9 seam recorded (T005 extension or follow-on task) and implemented in both repos.
- [ ] No file over the 150-line cap; ruff clean; no new dependencies; no secrets.
- [ ] Orchestrator has reconciled T006/T021 state in both repos' `docs/TODO.md` and
      recorded the G-B3 evidence in the task files.
