---
artifact: stage-todo
id: TODO-REPLAY-PORT
status: draft — pending orchestrator approval (workflow step 5, guidelines p. 9 §2.5)
version: 0.1
derived_from: PLAN-REPLAY-PORT@0.1 · PRD_replay_port (draft)
applies_to: police_repo + thief_repo
owner: orchestrator
updated: 2026-08-22
---

# TODO — Replay Port (headless Replay Viewer & replayable artifacts)

## How this ledger works

This is a **stage execution ledger** for the replay-port workstream, mirroring the
[stage-todo precedent](TODO_mcp_infrastructure.md). Stage tasks (RP-##) decompose the
[PLAN](PLAN_replay_port.md) into claimable units; each maps to one **repository task**
(T###) that exists (or is created in Phase 0) in **both** repos' `docs/tasks/` and board
rows in both repos' `docs/TODO.md`.

- The repository task file is authoritative for scope, bounded context, write set, and
  evidence; this ledger is the cross-repo index and phase ordering.
- `common/` work is written once and synced byte-identical to both repos (NFR-RP-06);
  per-repo work is done in each repo's own task instance (same T### id, role-substituted
  write set).
- Claiming rules are AGENTS.md's: set `claimed_by` + finite `claim_expires_at`, verify
  dependencies `done` and no `blocks: start` gate, edit only the declared write set,
  branch `task/T###-slug` where practical.
- Every stage task ends with its verification commands and the evidence the orchestrator
  validates before flipping status.

## Phase 0 — Orchestrator actions (ORC, before any claim)

These are governance actions, not implementation. None requires a worker; all are
required by the [PRD §10](PRD_replay_port.md) decisions and the PLAN §13/D-07 re-sequencing.

| ID | Action | Scope |
|---|---|---|
| O-01 | **Record ADRs** for D-01 (artifact shape) and D-02 (official-template stance / interop boundary) in both repos' `docs/decisions/` (next free ADR numbers; both repos identical) | AGENTS.md: ADR for a sufficiently important durable technical decision |
| O-02 | **Create task files** T033, T034, T046, T047 in both repos (`docs/tasks/T033-*.md` … `T047-*.md`, frontmatter sketches below) **and board rows** in both repos' `docs/TODO.md` (after T032) | D-07; new work gets a new task — scope never expands silently |
| O-03 | **Reconcile the board:** T008's row in both repos' `docs/TODO.md` is stale — the task file is `done` (2026-08-18 evidence, ST-09 resolution) while the board says `blocked`/`implementation_present`. Also record the standing ownership note for `common/transport/{subgame,series}.py` (modified by ST-09 outside T008's declared write set, per T008's "Deviations") so T034's claim on those paths is unambiguous | Keeps the "ready" derivation correct; avoids double ownership |
| O-04 | **T015 re-scope (proposal):** add T033 to T015's `depends_on`; move `tests/integration/test_replay_tamper.py` from T015's write set to T047's; T015 keeps `src/<peer>/ui/replay.py` + `tests/unit/replay/` | D-07; G6/G7. If the orchestrator declines, T047 takes only new test paths and T015's write set stands |

### Proposed task frontmatter (for O-02)

```yaml
# T033 — Replay shape adapter & headless harness (C03)
#   implements: SEC-005, SEC-006 (consumed); OBS-006 (verification engine)
#   depends_on: [T008]            # done per task file 2026-08-18 (O-03 reconciles the board)
#   gates: []
#   write_set: common/transport/replay_records.py, common/transport/replay.py,
#              tests/unit/transport/test_replay_records.py, tests/unit/transport/test_replay_verify.py
#   (new files only — no overlap with any declared write set)

# T034 — Per-subgame evidence capture in the series engine (C03)
#   implements: OBS-006 (evidence availability); SEC-005/SEC-006 (consumed)
#   depends_on: [T008] + O-03 ownership reconciliation
#   gates: []
#   write_set: common/transport/subgame.py, common/transport/series.py,
#              tests/unit/transport/test_series_evidence.py

# T046 — Replayable kit-shaped artifact emission, interop boundary (C06)
#   implements: REPORT-005..REPORT-009 (consumed via interop); OBS-006 (artifact availability)
#   depends_on: [T033, T034]
#   gates: []                    # deliberately NOT gated by INPUT-001/T016 (D-02: interop artifact)
#   write_set (per repo): src/<peer>/reporting/pipeline.py, src/<peer>/runner.py,
#              tests/unit/reporting/test_kit_artifacts.py, tests/integration/test_replayable_bundle.py

# T047 — Headless replay CLI, integration & tamper evidence (C05)
#   implements: OBS-006 (rule-20 gate exercised against real artifacts); OBS-007 (evidence honesty, consumed)
#   depends_on: [T033, T046]
#   gates: []
#   write_set (per repo): scripts/replay.py, tests/integration/test_replay_tamper.py (per O-04),
#              docs/evidence/replay-port/
```

## Stage task index

| Stage | Task | Repo task | Component | Depends on | Status |
|---|---|---|---|---|---|
| A | RP-01 Shape adapter + headless harness | T033 (both repos, shared slice) | C03 | T008 (done) | not_started |
| A | RP-02 Evidence capture in the series engine | T034 (both repos, shared slice) | C03 | T008 (done) + O-03 | not_started |
| B | RP-03 Replayable artifact emission | T046 (each repo) | C06 | T033, T034 | not_started |
| C | RP-04 CLI + integration/tamper evidence | T047 (each repo) | C05 | T033, T046 | not_started |

Phases A and B are per-repo mirrors of one shared design; Phase 0 must land first.
RP-01 and RP-02 are parallel-safe once O-01…O-03 are done (disjoint write sets).

## Phase A — Shared `common/transport` slice (write once, sync both)

### RP-01 — Shape adapter + headless harness (owner: IA → repo task T033, both repos)

Implements FR-RP-01…03, 08, 09, 10, 13 (shared half).

- Create `common/transport/replay_records.py` (PLAN §5.1): `from_kit_record`,
  `to_kit_record`, `flat_steps_to_kit_doc`, `is_foreign_record` — pure, round-trip
  identity, re-hash-exact.
- Create `common/transport/replay.py` (PLAN §5.2): `_terms_beside`, `verify_log`,
  `verify_dir`, `cross_check_uid` — imports `common.transport.*` only; own-shaped halves
  through `audit_records(flat, played={}, terms)`; foreign halves integrity-only with the
  degraded-coverage note (D-03); verdict split TAMPERED/ILLEGAL (FR-RP-08).
- Tests: `tests/unit/transport/test_replay_records.py` (TC-RP-06 differential round-trip
  over a fixture sweep; step-0 handling TC-RP-09), `tests/unit/transport/test_replay_verify.py`
  (TC-RP-02, TC-RP-03 ×4 physics variants, TC-RP-04, TC-RP-05, TC-RP-08, TC-RP-10 golden pins).
- Fixtures: a minimal honest kit-shaped log + config pair built through
  `to_kit_record` from real-shaped flat records (no reference-kit code — fixtures are ours).

**Verification:** `uv run pytest tests/unit/transport/test_replay_records.py tests/unit/transport/test_replay_verify.py` · `uv run ruff check common/transport tests/unit/transport` · line cap via `run_quality_gates.py` · `diff -rq` common/ across repos: 0 differing files.

**Evidence:** test output; the two new files' line counts; `diff -rq` result.

### RP-02 — Evidence capture in the series engine (owner: IA → repo task T034, both repos)

Implements FR-RP-04/05/06 (availability half). D-08 seam, PLAN §12.

- `common/transport/subgame.py`: add `SubGameEvidence` dataclass; `play_subgame` returns it
  (row, our_records incl. step-0, opponent revealed records, result_claim, terms); the live
  audit call is untouched.
- `common/transport/series.py`: `SeriesResult.evidence: dict[int, SubGameEvidence] | None =
  None` (additive); `PeerFacade.run` accumulates evidence from the driver.
- Tests: `tests/unit/transport/test_series_evidence.py` — evidence present after
  `run_series` over loopback (6 subgames, both sides); records re-hash clean against the
  commitments seen on the wire; `played` map never appears in any evidence field; existing
  `run_series`/facade consumers unchanged (their suites stay green without edits).

**Verification:** `uv run pytest tests/unit/transport tests/integration` (full existing series suites green, no edits) · ruff + line cap · `diff -rq` common/.

**Evidence:** test output; confirmation that no existing test file needed modification (source-compatibility of D-08).

## Phase B — Per-repo emission (each repo, mirrored)

### RP-03 — Replayable artifact emission (owner: IA → repo task T046, each repo)

Implements FR-RP-04…06, 11, 12 (emission half).

- `src/<peer>/reporting/pipeline.py`: extend `KitInteropAdapter` with `interop_label`,
  `kit_config_doc`, `kit_log_doc`, `kit_declaration_doc`, `kit_result_doc`; new
  `write_replayable_bundle` (PLAN §5.5) — canonical bytes + trailing newline, `replay/`
  subdirectory (D-05), `links` block per doc, `interop` block on every doc (FR-RP-12),
  `opponent_records` sealed by default (D-06).
- `src/<peer>/runner.py`: `write_artifacts` additionally emits the bundle when
  `result.evidence` is present; the root-level `result_*.json` summary is unchanged.
- Tests: `tests/unit/reporting/test_kit_artifacts.py` (doc shapes, labels, one-uid join,
  canonical-bytes property, line cap), `tests/integration/test_replayable_bundle.py`
  (TC-RP-01 honest end-to-end: loopback series → `write_artifacts` → bundle on disk →
  `verify_log` per log → Verified OK; TC-RP-07: internal `SubGameLog` attachment co-located
  at the artifacts root does not enter `replay/` and does not false-fail `verify_dir`).

**Verification:** `uv run pytest tests/unit/reporting tests/integration/test_replayable_bundle.py` · ruff + line cap on touched files · a real `--mode=warmup` run producing `artifacts/replay/` (both repos).

**Evidence:** one `artifacts/replay/` tree per repo (sanitized group ids, no secrets — `check_no_secrets` clean); listing + one log doc excerpt.

## Phase C — CLI, integration & tamper evidence (each repo, mirrored)

### RP-04 — Headless CLI + tamper suite + submission evidence (owner: IA → repo task T047, each repo)

Implements FR-RP-07; closes the rule-20 gate against real repo artifacts (G4).

- `scripts/replay.py` (PLAN §5.7): `replay <dir>` → per-log verdicts, `cross_check_uid`
  outcome, ok/bad summary, exit code 0 iff clean.
- `tests/integration/test_replay_tamper.py` (per O-04 ownership): TC-RP-02 (one-byte
  payload mutation → TAMPERED, named step, both hashes), TC-RP-05 (two-uid directory
  fails), TC-RP-10 (golden determinism), plus a CLI subprocess check of exit codes.
- Evidence directories under `docs/evidence/replay-port/` (both repos, sanitized):
  `verified_ok/` — a real warmup-run `replay/` set with the CLI transcript (Verified OK,
  counts stated, uid check clean) and `tampered/` — the identical tree with one byte
  flipped in one `payload`, transcript showing TAMPERED with the named step. These feed
  T023's real-evidence requirements (OBS-007/QR-017; App. C).

**Verification:** `uv run pytest tests/integration/test_replay_tamper.py` · `uv run python scripts/replay.py <evidence>/verified_ok` exit 0 · same over `tampered/` exit 1 · full repo gates (`run_quality_gates.py`) green.

**Evidence:** both transcripts, exit codes, byte-diff between the two trees (exactly one byte).

## TC coverage progression

| TC | Owner task | Covered when |
|---|---|---|
| TC-RP-01 honest bundle → Verified OK + uid join | RP-03 | M3 |
| TC-RP-02 one-byte mutation → TAMPERED | RP-01 (unit) + RP-04 (integration) | M1 / M4 |
| TC-RP-03 physics-only → ILLEGAL, never TAMPERED (4 variants) | RP-01 | M1 |
| TC-RP-04 two-sided `opponent_records` counted | RP-01 | M1 |
| TC-RP-05 mixed-uid directory rejected | RP-01 (unit) + RP-04 (CLI) | M1 / M4 |
| TC-RP-06 adapter round-trip differential | RP-01 | M1 |
| TC-RP-07 internal+kit co-location, no false failure | RP-03 | M3 |
| TC-RP-08 foreign-log degradation, no false tamper | RP-01 | M1 |
| TC-RP-09 step-0 re-hashes, not a verified move | RP-01 | M1 |
| TC-RP-10 golden determinism | RP-01 (unit) + RP-04 (integration) | M1 / M4 |

## Stage definition of done (replay-port gate)

- All of M1…M5 in [PRD §2.2](PRD_replay_port.md) demonstrated with evidence in both repos.
- `uv sync --locked --all-groups`, `uv run ruff check .`, `uv run pytest`,
  `uv run python scripts/run_quality_gates.py` — all green in **both** repos.
- `diff -rq` over `common/`: 0 differing files; per-repo mirrors in sync.
- ADRs (D-01, D-02) recorded in both repos; task files T033–T034, T046–T047 + board rows present in
  both repos; T008 board rows reconciled; T015 re-scope either approved and applied or
  explicitly declined (O-04).
- `docs/evidence/replay-port/{verified_ok,tampered}/` exist in both repos with transcripts;
  T023 may consume them.
- No new third-party dependency; no reference code vendored; internal reporting contract
  (`validate_schema` / `validate_identifiers` / `finalize_log`) untouched and green.

## Result and evidence (to fill at implementation)

- commit(s)/branch per stage task, per repo
- per-task verification output (tests, ruff, line cap, gates)
- `diff -rq` common/ results after RP-01 and RP-02
- the two evidence directories + CLI transcripts (RP-04)
