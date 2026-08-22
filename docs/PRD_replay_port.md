# PRD: Replay Port — Headless Replay Viewer & Replayable Match Artifacts

| Field | Value |
|---|---|
| **Workstream** | Replay port — headless replay verification (the checkable half of the book's Replay Viewer) + replayable artifact emission |
| **Primary component** | C05 Observability & Replay; shared C03 slice (integrity engine, `common/transport/`); per-repo C06 slice (artifact emission, `src/<peer>/reporting/`) |
| **Source chapters** | Project Book Ch. 7 (§7.4–7.5, The Replay Viewer and Integrity Enforcement), App. E rule 20 (TAMPERED disqualification), App. F table 20 (artifact names, shared `game_uid`) |
| **Compatibility target** | `references/copthief-league-protocol/sparring/replay.py` — read-only reference, never vendored ([LEAGUE_COMPATIBILITY](interop/LEAGUE_COMPATIBILITY.md): "Adapters, not lock-in") |
| **Applies to** | `police_repo` and `thief_repo` — one shared, role-parameterized plan; per-repo files under `src/<peer>/` (`thief_peer` / `police_peer`) |
| **Status** | draft — pending orchestrator approval (workflow step 5, guidelines p. 9 §2.5) |
| **Owner** | orchestrator |
| **Updated** | 2026-08-22 |

---

## 1. Overview & Context

### 1.1 Purpose

The book makes the Replay Viewer a **threshold submission**: load the final log, step through it, recompute SHA-256 over each sealed record, compare with the stored commitment, and display **Verified OK** or a red **TAMPERED** — one tampered record voids the match immediately, with no appeal (Ch. 7 §7.4–7.5; App. E rule 20).

This PRD covers the checkable, no-dependency half of that viewer — the **headless verifier** — plus the artifact emission that makes it meaningful for this project. The repositories today persist only a summary (`result_{game_id}.json` with per-subgame step *counts* and `audit_ok` booleans); the per-step sealed records exist in memory at end-of-game and are discarded. Without emission, a ported verifier reports *"no records — the game left nothing to verify"* for every local run.

The workstream therefore has two faces and one contract:

1. **Emit** — after every series (including `--mode=warmup`), persist a replayable, kit-shaped artifact set — `declaration_{game_id}.json`, `config_{game_id}_g{NN}.json`, `log_{game_id}_g{NN}.json`, `result_{game_id}.json` (the App. F table 20 names) — all sharing one `game_uid`, carrying the sealed per-step records of **both** sides.
2. **Verify** — headless entrypoints (`verify_log`, `verify_dir`, `cross_check_uid`) and a CLI that re-hash every sealed record through the **single canonical integrity path** (M-05) and report `Verified OK` / `TAMPERED` / `ILLEGAL`, deterministically, offline, on any copy of the directory — the reference's stated purpose of settling an audit dispute with a partner, plus a CI gate.

The verifier is **evidence, not a second rules engine** (C05 PRD constraint; T015 "Relevant context"): it consumes immutable artifacts and calls C03's existing audit algorithm (`[M-05](mechanisms/M-05-commit-reveal-integrity.md)`). It does not reimplement hashing. The only new crypto-adjacent code is a pure, deterministic **shape adapter** between the kit's nested sealed-record shape and the repository's flat record shape — provably round-tripping under canonicalization.

### 1.2 Problem statement

A decentralized match has no referee and no trusted history: each side's history lives in its own local log file, which opens the door to rewriting the past to win retrospectively. The book's answer is cryptographic: every step is sealed as (nonce, payload, commit) with `commit = SHA256(canonical(payload) + "|" + nonce)`, and the Replay Viewer re-derives every commitment from the visible log. Because collision resistance makes an alternative input producing the same hash unfindable, any alteration of (nonce, payload) is necessarily detected.

For this project the problem is concrete and local: the integrity engine already exists and already runs at live settlement (four-layer `audit_records`: re-hash → binding → physics → outcome), but

- nothing persists the per-step evidence to disk, so the engine's verdict can never be *re-shown* to a partner or a CI run;
- the reference verifier (`sparring/replay.py`) cannot be copied in directly — it reads a record/log/config shape our production code does not write, and it calls an audit API whose signature differs from ours;
- the task graph (T015) currently bundles the GUI viewer with this headless work and is blocked behind the GUI chain (T010/T014, PLANQ-007) and the official-template gate (T016/INPUT-001) that this work does not need.

### 1.3 Theoretical background

- **Commit–reveal with collision resistance.** The commitment `SHA256(canonical(payload) + "|" + nonce)` binds the mover to the full step payload (State, Move, Intent, Nonce per the Ch. 5 protocol) before reveal. Re-verification is binary: recomputed commitment equals the stored commitment, or it does not — there is no "almost matches" (Ch. 7 §7.5; App. E rule 20). The repository's primitives are byte-identical to the kit's pinned constructions — `verify_vectors.py`'s `ref_commit`, `ref_terms_signature`, `ref_game_uid`, `ref_game_id` — and reproduce the golden vectors (T008, done 2026-08-18).
- **Honest verdict split (anrbj666 finding, 2026-08-05, in the reference's own docstring).** "TAMPERED" means exactly one thing: a record did not reproduce its commitment — and it voids the game. A physics or binding failure is a *different* verdict (here: ILLEGAL) and gets a different word, or an honest team is told it forged a log it did not forge. A diagonal move is not a forgery. The reference `AuditResult` keeps the two apart for exactly this reason: "a caller that reports 'does not reproduce its commitment' over a physics complaint sends an honest team hunting a serialization bug it does not have."
- **The intent binding is a requirement, and the kit's audit never required it.** SEC-003/M-05 bind at least State, Move, Intent, and Nonce in every commitment, so the repo's audit requires a non-empty `intent` in every record; the kit's audit (a conformance reference, not a requirements document) never required it. The asymmetry is exactly why foreign logs need a degradation note (D-03) — and the kit's audit states that contract in its own docstring: a reveal that carries less evidence "gets the checks the evidence supports and a note for the one it cannot, never an accusation".
- **Local truth.** Every sealed record carries only the mover's own position and locally known barriers (`grid=…;self=[r, c];barriers=…`), never the opponent's objective position — the Dec-POMDP observation constraint (Ch. 7 §7.2) survives sealing.
- **Determinism and offline re-verification.** Replay output is a pure function of artifact bytes; the same directory always yields the same verdict, on any machine, with no network and no third-party dependencies. The binding layer (revealed vs received commits) is in-play knowledge and is intentionally inert offline — replay certifies integrity + physics; the live audit is all three.
- **Observability.** Live monitoring ("what is happening now?") and retrospective proof ("did the past really happen as claimed?") are distinct needs; this workstream is the latter (Ch. 7 §7.2, course Observability principle).

### 1.4 Target audience

- **The project team** — runs the verifier after every local series (including warmup) as a quality gate; keeps a verified-OK artifact directory as submission evidence (App. C).
- **A partner team** — receives a directory, runs `scripts/replay.py` offline, settles an audit dispute with a machine verdict (the reference's stated purpose).
- **CI** — deterministic, dependency-free, exit-code-driven.
- **Lecturer/evaluator** — inspects the replayable artifacts and the Verified-OK evidence without trusting either team's claims.

### 1.5 Anything missing before the port? (verified against repo code, task files, and the reference kit — 2026-08-22)

The cryptographic foundation is complete: byte-identical in both repos (`common/` diff clean) and byte-identical to the kit's pinned constructions in `verify_vectors.py`. What is missing, gap by gap — each gap's evidence column names the primary source it was checked against:

| # | Gap | Evidence | Closed by |
|---|---|---|---|
| G1 | **No persisted per-step records.** `write_artifacts` persists only `result_{game_id}.json` (counts + `audit_ok`); `play_subgame` builds both record halves in memory (`our_records` incl. step-0, opponent's revealed records) and returns only a `SeriesRow`. `build_sub_game_log` has zero production callers. | `src/<peer>/runner.py`, `common/transport/subgame.py` | FR-RP-04, FR-RP-05; PLAN §5.3–5.5, §12 |
| G2 | **No `config_*.json` carrying `terms` beside the logs.** Two mismatches: the internal config file is named `sub_game_config_{uid}_{id}.json` (the reference globs `config_*.json`), and terms live under `agreed_terms` (the reference reads `doc["terms"]`). The physics layer can never arm offline. | `src/<peer>/reporting/schemas.py` | FR-RP-05; decision D-04 |
| G3 | **Record-shape mismatch.** The reference reads nested `{payload, nonce, commit}` and calls `audit_records(recs, board_size=…, barriers_max=…, max_steps=…)`; the repo's `audit_records(records, played, terms, …)` takes flat records with a required positional `played`. Re-hashing is an exact match through the shape adapter; physics is the only real delta. | `common/transport/audit.py` vs reference | FR-RP-09; PLAN §5.1, §10 |
| G4 | **No headless entrypoint.** No `verify_log`/`verify_dir`/`cross_check_uid`, no CLI, no test loading a persisted artifact. The rule-20 gate is unexercised against real repo artifacts. | repo-wide | FR-RP-01, FR-RP-03, FR-RP-06, FR-RP-07 |
| G5 | **Official templates OPEN.** T016 is `blocks: start` on INPUT-001. The kit-shaped log must stay an interop artifact behind the existing `KitInteropAdapter` boundary, not a relabeling of the official `SubGameLog`. | `docs/tasks/T016-*.md`, `src/<peer>/reporting/pipeline.py` | FR-RP-12; decision D-02 |
| G6 | **Task graph blocks the port.** T015 is `blocked` (depends on T008/T010/T014); T014 is gated `blocks: start` by PLANQ-007 (GUI toolkit, `TBD_TEAM_DECISION`). The headless work needs none of that chain. | `docs/TODO.md`, task files | Decision D-07 (re-sequencing: new tasks T033–T036) |
| G7 | **Write-set mismatch.** T015 declares only `src/<peer>/ui/replay.py` + 2 test paths; the port also touches `common/transport/*` (C03), `src/<peer>/reporting/*` (C06), `src/<peer>/runner.py`, `scripts/replay.py`. `src/<peer>/ui/` does not exist yet (T014 owns it). | T015 frontmatter, AGENTS.md write-set governance | Decision D-07; TODO Phase 0 |
| G8 | **`log_*.json` filename collision.** The internal `SubGameLog` filename is `log_{game_uid}_{game_id}.json` (`kind == "log"`), which matches the reference's `verify_dir` glob. A mixed directory false-fails on the internal log (`steps`, not `records`) → "no records" on honest artifacts. | `src/<peer>/reporting/schemas.py` | FR-RP-11; decision D-05 |
| G9 | **Foreign-log degradation.** Repo physics parses the `state` string (foreign kit payloads carry `position` lists instead) → position checks silently inert; and repo layer 1 flags missing `intent` as TAMPERED (the kit audit has no such requirement) → false tamper accusation, violating T015's "unknown optional fields degrade…" acceptance criterion. Own artifacts always carry both fields, so the primary use case is unaffected. | `common/transport/audit.py`, `common/transport/audit_physics.py` | FR-RP-10; decision D-03; PLAN §7 flow |
| G10 | **Offline-audit API specifics.** The harness must pass `played={}` (binding layer correctly inert offline, matching the reference) and preserve the TAMPERED (hash miss) vs ILLEGAL (physics) verdict split. | `common/transport/audit.py` | FR-RP-08; PLAN §5.2 |

**Answer: yes — 10 gaps, none of them cryptographic.** The single SHA-256 path, the nonce, the four-layer audit, and the kit-matching `game_uid` derivation all exist and are verified; what is missing is the *evidence plumbing* (G1, G2), the *shape bridge* (G3), the *entrypoint* (G4), and the *governance* (G5–G7, G8).

## 2. Goals & Success Metrics

### 2.1 Goals

- **GP-01**: A partner or CI can verify any series this repository writes — integrity and physics, offline, deterministically — from a directory alone.
- **GP-02**: One tampered record voids the game with a named step and both hashes shown; a physics-only failure is reported ILLEGAL and never TAMPERED (App. E rule 20; anrbj666 finding).
- **GP-03**: Every local series (including warmup) leaves all four joinable artifacts with one shared `game_uid` (App. F table 20).
- **GP-04**: The verifier reuses the single canonical integrity path (M-05); no second hash construction, no vendored reference code.
- **GP-05**: The headless work unblocks without the GUI chain (T010/T014/PLANQ-007) and without the official-template gate (T016/INPUT-001).
- **GP-06**: The work lands in both repos with `common/` byte-identical and per-repo mirrors in sync.
- **GP-07**: Foreign kit logs degrade to visible, explicitly-limited verification instead of false tamper accusations (T015 acceptance criterion).
- **GP-08**: Submission evidence exists: a real-run directory that verifies OK and a one-byte-flipped copy that verifies TAMPERED (feeds T023; App. C).

### 2.2 Success criteria (milestones)

| Milestone | Criterion |
|---|---|
| M1 — shared slice | `common/transport/replay_records.py` + `replay.py` in both repos, byte-identical; adapter round-trip and verdict-split unit tests green; line cap + Ruff clean |
| M2 — evidence plumbing | `play_subgame`/`PeerFacade` carry per-subgame evidence up to `SeriesResult`; existing suites unchanged in verdicts |
| M3 — emission | a warmup run writes `artifacts/replay/` with declaration + 6 config + 6 log + 1 result, one `game_uid`; internal bundle artifacts untouched |
| M4 — headless proof | `scripts/replay.py artifacts/replay/` → `Verified OK` (all records, both halves counted); tampered copy → `TAMPERED` with named step; mixed internal+kit directory does not false-fail |
| M5 — governance | ADRs recorded; task graph updated (T033–T036 created, T015 re-scoped if approved); both repos' boards reconciled |

### 2.3 KPIs

| KPI | Target |
|---|---|
| Sealed records re-hashed per verified log | 100% of `records` + `opponent_records` (the report states the count and which side) |
| False TAMPERED verdicts on honest artifacts | 0 — including internal bundle artifacts co-located in the same tree (G8) |
| Detection: 1-byte payload mutation | 100% → TAMPERED, named step, both hashes in `detail` |
| Physics-only failure mislabeled TAMPERED | 0 (ILLEGAL, `tampered_steps == []`) |
| New third-party dependencies | 0 |
| New code files over 150 nonblank/noncomment lines | 0 |
| Cross-repo `common/` drift after each shared-slice task | 0 differing files (`diff -rq`) |
| Verdict determinism | byte-identical report for identical artifact bytes (golden-pinned) |

## 3. Functional Requirements

Priorities: P0 = rule-20 gate, P1 = interop honesty, P2 = polish.

- **FR-RP-01 (P0)** — `verify_log(path) -> (ok, report)`: load one kit-shaped log document, re-verify every sealed record, return a boolean plus a human-readable report. Verdicts are exactly `Verified OK`, `TAMPERED`, or `ILLEGAL`, using the reference's wording; one TAMPERED means the game is void (no repair path — C05 invariant).
- **FR-RP-02 (P0)** — Every re-hash goes through `common.transport.canonical.canonical_bytes` + `commit` (the single integrity path, M-05). No other hash construction may appear in the new code; the verifier imports `common.transport.*` only — never the reference kit.
- **FR-RP-03 (P0)** — Two-sided logs: when the document seals `opponent_records` beside its own, **every** sealed record in the file is re-hashed and the report says how many records of which side were certified (the anrbj666 two-sided finding).
- **FR-RP-04 (P0)** — Per-subgame emission: after every series, the repository persists a kit-shaped `log_{game_id}_g{NN}.json` per subgame whose `records` carry this side's sealed records (step-0 declaration record first) and whose `opponent_records` carry the opponent's revealed records (two-sided by default, D-06).
- **FR-RP-05 (P0)** — Terms beside the logs: a `config_{game_id}_g{NN}.json` per subgame with a top-level `terms` (the signed 14-key set) arms the offline physics layer (board size, barrier quota, step ceiling) — decision D-04.
- **FR-RP-06 (P0)** — One join key: all four artifacts (declaration, config, log, result) in the replayable set share one `game_uid`; `cross_check_uid(root) -> str | None` reports a conflict when a directory mixes uids — "a replay that verifies every record of a log belonging to a *different* match has proved nothing at all".
- **FR-RP-07 (P0)** — CLI: `scripts/replay.py <dir>` prints per-log verdicts (recursive `log_*.json`), the `cross_check_uid` outcome, and an ok/bad summary; exit code 0 only when every log verifies and the uid check is clean.
- **FR-RP-08 (P0)** — Honest verdict split (G10): re-hash miss (or missing commitment/withheld step relative to `played`) ⇒ **TAMPERED**; physics failure with a clean re-hash ⇒ **ILLEGAL**; the harness calls `audit_records(flat, played={}, terms)` so the binding layer is inert offline exactly as in the reference.
- **FR-RP-09 (P0)** — Shape adapter: pure, deterministic `from_kit_record` / `to_kit_record` (and list-level `flat_steps_to_kit_doc`) with round-trip identity under canonicalization; re-hashing `from_kit_record(r)` reproduces `r["commit"]` byte-for-byte.
- **FR-RP-10 (P1)** — Foreign-log degradation (G9): a record whose payload carries no parseable `state` string (foreign kit shape) is verified **integrity-only**, the report explicitly states the degraded coverage (physics not verifiable; intent not enforced for foreign records), and no placeholder field is ever invented — a placeholder would change the payload and break the re-hash.
- **FR-RP-11 (P1)** — Replayable-directory segregation (G8): kit-shaped artifacts live in a dedicated subdirectory (D-05) so `verify_dir`'s `log_*.json` glob can never match an internal `SubGameLog` attachment and false-fail on honest artifacts.
- **FR-RP-12 (P2)** — Interop labeling: every kit-shaped artifact carries an explicit `interop` block marking it `INTERNAL/INTEROP — NOT OFFICIAL`, produced behind `KitInteropAdapter` (G5); the official templates (T016/INPUT-001) replace the adapter when they arrive.
- **FR-RP-13 (P0)** — Determinism: report text is a pure function of artifact bytes; golden tests pin the exact verdict lines for the reference fixtures and for the repo's own honest bundle.

## 4. Non-Functional Requirements

- **NFR-RP-01 (no second rules engine)** — the verifier consumes immutable artifacts and calls C03's audit algorithm; it never re-derives game legality beyond the armed physics layer (C05 PRD constraint).
- **NFR-RP-02 (single integrity path)** — one `canonical_bytes` + `commit` construction (AGENTS.md "One canonical integrity path"); OPEN-007 (official envelope) remains open exactly as it does for live audit — this workstream neither resolves nor aggravates it.
- **NFR-RP-03 (no vendoring)** — reference material is read-only; no reference code or configuration enters project source (LEAGUE_COMPATIBILITY, AGENTS.md prohibited operations).
- **NFR-RP-04 (no new dependencies)** — standard library only; `uv sync --locked` stays clean.
- **NFR-RP-05 (line cap & module discipline)** — new code files ≤ 150 nonblank/noncomment lines (AGENTS.md; enforced by `scripts/check_line_cap.py`); narrow modules, descriptive names, decision-oriented docstrings.
- **NFR-RP-06 (cross-repo identity)** — every `common/` change is written once and synced byte-identical to both repos; per-repo files mirror each other (`src/<peer>/`).
- **NFR-RP-07 (local truth preserved)** — no artifact, report, or log field may carry the opponent's objective position; the sealed `state` string already contains own position only.
- **NFR-RP-08 (no secrets in artifacts)** — the existing reporting secret-scan discipline extends to the new artifacts (no tokens, credentials, or private identifiers).
- **NFR-RP-09 (determinism & testability)** — injectable filesystem/clock seams where I/O occurs; zero network, zero live external calls in tests; golden-pinned outputs.
- **NFR-RP-10 (non-invasive)** — internal reporting contract unchanged: `validate_schema` / `validate_identifiers` / `finalize_log` immutability and the internal `SubGameLog` schema stay intact; the kit-shaped set is additive.

## 5. Expected Input / Output

### 5.1 Input (to the verifier)

- A **replayable directory** (see PLAN §10) containing, per series: `declaration_{game_id}.json`, `config_{game_id}_g{NN}.json` ×6, `log_{game_id}_g{NN}.json` ×6, `result_{game_id}.json` — all carrying one `game_uid`, written as canonical bytes.
- Optionally a **foreign** kit-shaped directory (anrbj666-style) — verified under the degradation contract (FR-RP-10).

### 5.2 Output (from the verifier)

- `verify_log`: `(bool, str)` — `Verified OK — N records re-hashed against their commitments (both sides' sealed half)`, or `TAMPERED — steps … do not reproduce their commitments` / `ILLEGAL — every record re-hashes, but steps … break the signed physics`, with `AuditResult.detail` (named steps, both hashes).
- `verify_dir`: `(ok_count, bad_count, lines)`.
- `cross_check_uid`: `None` or a conflict report naming the distinct uids.
- CLI: the above printed; exit code 0/1.

### 5.3 Output (from the emitter)

- The replayable directory described in §5.1, produced by `src/<peer>/runner.py::write_artifacts` after every series (existing `result_*.json` summary at the artifacts root is unchanged — additive emission only).

## 6. Constraints & Limitations

**Constraints**

- Shared `common/` must remain byte-identical across both repos (write once, sync both).
- No new third-party dependencies; no vendored reference code.
- Do not weaken TAMPERED semantics: one re-hash miss voids the game; keep the ILLEGAL-vs-TAMPERED split; replay never "fixes" a verdict (C05 invariant).
- Do not break the internal reporting contract (`validate_schema` / `validate_identifiers` / `finalize_log`).
- Governance: ADRs for the durable decisions (D-01, D-02); claim before implementing; edit only declared write sets; new task files for new scope (AGENTS.md).

**Limitations (documented, not defects)**

- **Binding layer is offline-inert by design.** The revealed-vs-received commit binding needs the in-play `played` map; offline replay certifies integrity + physics. A *missing* step (gap in step numbers) is not detectable offline by either the reference or this port — the live audit catches it, and the GUI viewer (T015) can check completeness against the expected step count once it has the result artifact in context.
- **Foreign logs verify integrity-only.** Physics needs the sealed `state` string (own shape); foreign payloads carry `position` lists. Extending `check_physics` to foreign shapes is C03 scope creep — explicitly deferred (decision D-03).
- **Not official.** Until T016/INPUT-001 resolves, the kit-shaped set is an interop artifact (D-02); official submission artifacts remain the internal contract (T032/T016) plus the signed report (T018).
- **One directory, one match.** `verify_dir` + `cross_check_uid` operate on a directory believed to hold one match; the uid check is the guard, and mixed-match directories fail it loudly.

## 7. Alternatives Considered

| Alternative | Verdict | Rationale |
|---|---|---|
| Vendor the reference `replay.py` + kit `audit.py` as-is | **Rejected** | LEAGUE_COMPATIBILITY forbids third-party code in project source; it would create a second hash path and a second audit engine (C05 invariant) |
| Retrofit kit-shaped `records` into the internal `SubGameLog.steps` | **Rejected (for now)** | the official template (T016) is open; relabeling an internal contract as the official log is prohibited (T016 "Relevant context"); the interop artifact is the sanctioned boundary (G5) |
| Teach `_terms_beside` to read the internal `sub_game_config_*` + `agreed_terms` | **Rejected** | the harness would diverge from the reference and the replayable directory would no longer be self-contained for a partner (D-04) |
| Emit the replayable set in a separate top-level directory (not under the artifacts root) | **Considered** | workable, but splits one match's evidence across trees; a dedicated subdirectory under the artifacts root keeps one root while fixing G8 (D-05) |
| Evidence seam: callback sink injected into `PeerConfig` | **Considered** | hides the evidence flow in configuration; the result object is the canonical place where the runner already reads |
| Evidence seam: driver writes a side-channel journal file | **Rejected** | bypasses the result contract, adds a second persistence path, complicates determinism |
| Evidence seam: `play_subgame` returns row + evidence; `SeriesResult` carries it (additive optional field) | **Chosen** | data rides the canonical result object; additive default keeps every existing consumer (facade, runner, tests) source-compatible (PLAN §12) |
| Widen T015's write set to cover the whole port | **Rejected** | T015 is the GUI viewer and is blocked behind PLANQ-007; coupling the headless gate to a GUI-toolkit team decision leaves the rule-20 gate unexercised indefinitely (D-07) |

## 8. Success Criteria & Test Plan

### 8.1 Verification flow (per log, per side)

```mermaid
flowchart TD
    S[Load log document] --> E{records present?}
    E -- no --> NF[FAIL: no records<br/>the game left nothing to verify]
    E -- yes --> F{Foreign shape?<br/>payload has position,<br/>no parseable state}
    F -- yes --> DEG[Degraded path: integrity-only re-hash<br/>via the same canonical_bytes + commit<br/>report notes: physics not verifiable,<br/>intent not enforced (foreign)]
    F -- no --> AD[Adapter: kit record → flat record<br/>round-trip identity]
    AD --> AU[audit_records flat, played={}, terms<br/>from config_*.json beside the log]
    AU --> V{tampered_steps non-empty?}
    DEG --> V
    V -- yes --> T[TAMPERED — steps N do not reproduce<br/>their commitments — game void]
    V -- no --> P{failed_steps non-empty?}
    P -- yes --> I[ILLEGAL — every record re-hashes,<br/>but steps N break the signed physics]
    P -- no --> OK[Verified OK — N records re-hashed<br/>count of sealed sides stated]
```

### 8.2 Specific test cases

The case families mirror the reference closure suite (`sparring/tests/test_audit_closure.py`: the founding fabricated-log probe, foreign vocabularies, binding, physics, settlement rule), re-expressed for the offline harness: the binding layer stays inert offline (the `played` map is in-play knowledge) and the settlement rule maps onto the verdict split.

| TC | Case | Expectation |
|---|---|---|
| TC-RP-01 | Honest bundle from the real emitter (real driver records, step-0 first) | `Verified OK`; `cross_check_uid` passes (one `game_uid` across declaration/config/log/result) |
| TC-RP-02 | One byte mutated inside a `payload` | `TAMPERED`, named step, `detail` shows committed + rehash |
| TC-RP-03 | Physics-only failure, each of: off-board position / diagonal trail / over barrier quota / over step ceiling | `ILLEGAL`, `tampered_steps == []` — never TAMPERED |
| TC-RP-04 | Two-sided log with `opponent_records` | both halves re-hashed; report counts both sides |
| TC-RP-05 | Directory mixing two different `game_uid`s | `cross_check_uid` names both uids and the run fails |
| TC-RP-06 | Adapter differential: `to_kit_record(from_kit_record(r)) == r` over a fixture sweep | round-trip identity, canonical bytes equal |
| TC-RP-07 | G8 regression: internal `SubGameLog` attachment mixed with kit-shaped artifacts | no false failure on the internal log (segregated layout honored) |
| TC-RP-08 | G9 degradation: foreign log without `intent` / without `state` | report states degraded coverage; no tamper accusation |
| TC-RP-09 | Step-0 declaration record | re-hashes clean, counted in the record total, not counted as a verified move (`verified_steps` counts `step >= 1`) |
| TC-RP-10 | Golden determinism: identical artifact bytes, two runs | byte-identical report text |

### 8.3 Milestones and deliverables

- **M1** — `common/transport/replay_records.py`, `common/transport/replay.py` (+ unit tests) in both repos, byte-identical. Deliverable: shared-slice test evidence (`uv run pytest`, Ruff, line cap, `diff -rq`).
- **M2** — evidence plumbing in `common/transport/{subgame,series}.py` (+ tests). Deliverable: unchanged verdicts on the existing series suites + new evidence-capture tests.
- **M3** — per-repo emission (`src/<peer>/reporting/pipeline.py` extension, `src/<peer>/runner.py`). Deliverable: a warmup-run `artifacts/replay/` directory (both repos) with all four artifact kinds and one `game_uid`.
- **M4** — `scripts/replay.py` + integration/tamper suite. Deliverable: Verified-OK and TAMPERED evidence directories under `docs/evidence/replay-port/` (both repos), feeding T023's real-evidence requirements.
- **M5** — governance closeout: ADRs, task files T033–T036, board rows, T015 re-scope (if approved), board reconciliation for T008.

## 9. Out of Scope (for this workstream)

- The **GUI half** of the book's Replay Viewer — forward/backward navigation, per-step display, Verified-OK screenshot capture — remains T015 (C05) with its existing gates (T010/T014, PLANQ-007); the headless harness is what T015 will display.
- **Official schema adoption** (T016/INPUT-001) and the signed-report integration (T018) — the kit-shaped set is an interop artifact until the official templates arrive (D-02).
- **Extending `check_physics` to foreign payload shapes** (position-list physics) — C03 scope, deferred (D-03).
- **Live binding-layer re-verification** (replaying against a persisted `played` map) — in-play knowledge, intentionally not persisted (local truth + minimal evidence).
- **Lecturer-facing submission packaging** beyond the evidence directories (T023/T026).
- Any change to the 14-key signed terms, the canonicalization, or the commit construction (OPEN-007 territory, T008's proven primitives).

## 10. Open items & decisions

Decisions D-01…D-08 are recorded in [PLAN_replay_port.md](PLAN_replay_port.md) §13 with rationale and alternatives; D-01 and D-02 are promoted to ADRs at approval (AGENTS.md: ADR for a sufficiently important durable technical decision).

| ID | Decision | Recommendation (pending approval) |
|---|---|---|
| D-01 | Artifact shape | Kit-shaped `log_`/`config_`/`declaration_`/`result_` docs per the App. F table 20 names — the reference kit's artifact writer states in its docstring that its names and the shared `game_uid` "follow the book's App. F table 20 exactly" — each record `{payload, nonce, commit}`, all sharing one `game_uid`, written as canonical bytes |
| D-02 | Official-template stance (G5) | The kit-shaped log is a **parallel interop artifact behind `KitInteropAdapter`** — not written into the official `SubGameLog`; T016 replaces the adapter when it resolves |
| D-03 | Foreign-log policy (G9) | Integrity-only + explicit degraded-coverage note; never invent a placeholder field (it would break the re-hash) |
| D-04 | Terms lookup (G2) | Emit kit-shaped `config_*.json` with top-level `terms` (harness stays reference-identical; directory self-contained) |
| D-05 | Replayable-directory layout (G8) | Dedicated `replay/` subdirectory under the artifacts root; `verify_dir`/`cross_check_uid` operate on that clean set |
| D-06 | Two-sided logs | Seal `opponent_records` in our own kit-shaped logs (stronger evidence; matches the counted league logs) |
| D-07 | Task-graph re-sequencing (G6/G7) | New tasks T033 (shared adapter+harness), T034 (evidence plumbing), T035 (per-repo emission), T036 (CLI + integration/tamper evidence); T015 stays the GUI viewer and gains a dependency on T033; orchestrator approves the widened/new write sets |
| D-08 | Record-capture seam (G1) | `play_subgame` returns row + per-subgame evidence; `SeriesResult` carries an additive optional `evidence` map (PLAN §12) |

## 11. References

- Book Ch. 7 — `wikis/project-book/Project-chapter-7-gui.md` in the shared project wikis (Replay Viewer, integrity enforcement, rule 20, App. C evidence).
- Component contract: [C05 PRD](components/C05-observability-replay/PRD.md) (OBS-005, OBS-006, invariants, no-second-rules-engine constraint); [C05 PLAN](components/C05-observability-replay/PLAN.md).
- Mechanism: [M-05 Commit–Reveal Integrity](mechanisms/M-05-commit-reveal-integrity.md); contract: [CT-04 Canonical Bytes](contracts/CT-04-canonical-bytes.md).
- Task: [T015 — Implement Replay And Audit View](tasks/T015-implement-replay-and-audit-view.md); gates: [T014](tasks/T014-implement-live-gui.md) (PLANQ-007), [T016](tasks/T016-adopt-official-report-artifact-schemas.md) (INPUT-001); evidence consumer: [T023](tasks/T023-complete-documentation-and-real-evidence.md).
- Interop policy: [LEAGUE_COMPATIBILITY.md](interop/LEAGUE_COMPATIBILITY.md); open items: [OPEN_QUESTIONS.md](spec/OPEN_QUESTIONS.md) (OPEN-001, OPEN-007); ADR precedent: [ADR-004](decisions/ADR-004-operational-interoperability-profile.md), [ADR-005](decisions/ADR-005-shared-protocol-layer-placement.md).
- Reference kit (read-only, never vendored — LEAGUE_COMPATIBILITY): `references/copthief-league-protocol/verify_vectors.py` (pinned canonical/commit/uid constructions), `…/sparring/replay.py` (verifier, verdict wording, two-sided finding), `…/sparring/audit.py` (four-layer audit, tampered/failed split, degradation contract), `…/sparring/kitref.py`, `…/sparring/artifacts.py` (App. F table 20 artifact names), `…/sparring/cli.py` (`replay` command and exit codes), `…/sparring/tests/test_audit_closure.py` (test-case families).
- Repo inventory verified for §1.5 (2026-08-22): `common/transport/{canonical,integrity,ids,audit,audit_physics,subgame,series,inbox}.py`; `src/<peer>/reporting/{schemas,artifacts,pipeline}.py`; `src/<peer>/runner.py`; task files [T008](tasks/T008-implement-integrity-core.md), [T014](tasks/T014-implement-live-gui.md), [T015](tasks/T015-implement-replay-and-audit-view.md), [T016](tasks/T016-adopt-official-report-artifact-schemas.md); [TODO.md](TODO.md); [OPEN_QUESTIONS.md](spec/OPEN_QUESTIONS.md) (OPEN-001, OPEN-007); [M-05](mechanisms/M-05-commit-reveal-integrity.md) (SEC-003).
- Sibling documents: [PLAN_replay_port.md](PLAN_replay_port.md), [TODO_replay_port.md](TODO_replay_port.md); precedent for stage documents: [PRD_mcp_infrastructure.md](PRD_mcp_infrastructure.md), [PLAN_mcp_infrastructure.md](PLAN_mcp_infrastructure.md), [TODO_mcp_infrastructure.md](TODO_mcp_infrastructure.md).
- Governance: [AGENTS.md](../AGENTS.md); system [PRD](PRD.md), [PLAN](PLAN.md), [TODO](TODO.md).
