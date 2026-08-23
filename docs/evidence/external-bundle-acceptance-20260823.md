# External Bundle Acceptance — Police — 2026-08-23

`M006 — External Bundle Handoff Acceptance`. Maintenance/evidence task.
Requirement IDs: ARCH-008, QR-001, QR-002, QR-004, QR-006, QR-010, QR-011, QR-019, SUB-001.

> **Deviation note:** The external session's terminal handoff document was not supplied.
> M006 was executed against the pushed `lahav-tasks` heads as a read-only acceptance audit,
> reproducing refs, changed files, tests, gates and evidence directly. Claims that the
> external handoff would have carried (exact commands, per-task commit attribution, PR
> body/status) are recorded from the pushed branch state and marked `unverified` where the
> handoff was the only source. This deviation is recorded here and in the Thief counterpart.

## Input hashes

| Input | Expected SHA-256 | Verified |
|---|---|---|
| `police-thief-llm-replay-kit-final-run-2026-08-23 (1).zip` | `1d07e5a86e144ea08e6ef09e067ceaf7b32c5a05d035a6aa96432a47eedd0323` | `unverified` (ZIP not present in workspace) |
| `00_MASTER_ORCHESTRATOR_PROMPT (1).md` | `f1fe3feb341cc411cd24916f0f3a6dea250e44c754831e7b0a3e8285b594d6f3` | `unverified` (file not present in workspace) |

The pinned kit commit `ad6557626587e09146af4283a5e808e7001343c5` is represented by the
vendored fixtures under `tests/fixtures/league_kit/ad65576/`. All four vector hashes were
reproduced exactly (see `Reproduced commands`). This is `kit_interop` evidence only.

## Git state

| Field | Value |
|---|---|
| Repository | `github.com:evya1/police_repo` |
| Local branch | `lahav-tasks` |
| HEAD | `7460023ffcc725529288089740a6f692df35b696` |
| Remote feature head (`origin/claude/replay-llm-completion-20260823`) | `7460023ffcc725529288089740a6f692df35b696` |
| `origin/master` | `c674eb8334e43da140e44a0320df0846682487d1` |
| Dirty worktree | clean (no tracked changes) |
| Unpushed commits | 0 (HEAD equals remote feature head) |
| Divergence from remote feature head | 0 left / 0 right |

The local `lahav-tasks` branch is byte-identical to the pushed external feature branch head.
No upstream is configured; the remote feature head is used as the acceptance anchor.

## Commit-to-task map

Commits on `origin/master..HEAD` (newest first):

| SHA | Task/scope |
|---|---|
| `7460023` | docs: hunk-level provenance map for the llm-provider partner branch |
| `7ccb530` | T054 live audit physics prefers the explicit sealed position |
| `e5f38ec` | T054 wire reference-v3 audit adapter, stable opponent pin, sealed position |
| `1d9b142` | docs: reconcile actual kit checkpoint status and resolve PLANQ-007 |
| `4998634` | T052 reference-v3 protocol and lifecycle compatibility (anti-corruption adapter) |
| `887b476` | T049 provider-neutral language model adapter |
| `76037b1` | docs: narrow README correction from verified branch state (T023/T024/T026 remain open) |
| `f23ef94` | Governance: ADR-011, T052, T053, amended T022 for league-kit interoperability |
| `0550f4c` | T040 (partial): honest production line-cap ratchet, source_dirs blind spot repaired |

## Changed-file/write-set audit

The changed files map to the declared external write sets (T049, T052, T054, T040,
governance/ADR-011, T022 amendment, provenance docs, README/TODO corrections). No
unexpected production files were observed. Representative changed paths:

- `common/transport/*` (audit_physics, audit_wire, league_kit_envelope, opponent_pin,
  replay_evidence, run_series, series, subgame)
- `src/police_peer/infra/llm_client.py`, `src/police_peer/infra/llm_provider.py`
- `src/police_peer/sdk.py`, `src/police_peer/wire/*`
- `docs/decisions/ADR-011-league-kit-interoperability-boundary.md`
- `docs/provenance/llm-provider-branch-reconciliation.md`
- `docs/tasks/T022/T040/T049/T051/T052/T053/T054*.md`
- `tests/fixtures/league_kit/ad65576/*`
- `scripts/check_line_cap.py`, `scripts/line_cap_ratchet.py`, `config/repo_quality.toml`

## Reproduced commands

| Command | Exit | Summary |
|---|---|---|
| `git rev-parse HEAD` | 0 | `7460023ffcc725c529288089740a6f692df35b696` |
| `git status --short --branch` | 0 | `## lahav-tasks` (clean) |
| `git diff --check` | 0 | no whitespace errors |
| `git rev-list --left-right --count origin/claude/replay-llm-completion-20260823...HEAD` | 0 | `0 0` (identical) |
| `uv run ruff check .` | 0 | All checks passed |
| `uv run pytest -q` | 0 | 5300 statements, 450 missing, coverage 91.51% (>=85%) |
| `uv run python scripts/run_quality_gates.py` | 0 | all 7 generic gates passed |
| `uv run python scripts/check_planning_graph.py` | 1 | FAIL: 55 planning-graph issue(s) (pre-T040 debt) |
| `uv run python scripts/check_line_cap.py` | 0 | 273 files within 150 lines (5 baselined) |
| `uv run python scripts/check_replay_parity.py --sibling-root ../thief_repo` | 0 | shared_hash_problems: [] |
| `sha256sum vectors/*.json` (kit fixtures) | 0 | all four match pinned PROVENANCE.md hashes |

## External scope verdicts

| Scope | Verdict | Basis |
|---|---|---|
| Governance / M000 / PR truth | `accepted` | ADR-011, provenance map, README/TODO corrections present and coherent |
| T013 Step 0 / token ledger | `not_executed` | no T013 commit/evidence on this branch |
| T014/T015 Live/Replay GUI | `not_executed` | no GUI implementation/evidence on this branch |
| T050 conditional vendor | `not_executed` | blocked; no PLANQ-003 record on this branch |
| T051 provider-neutral composition | `not_executed` / `pending` | only its prerequisite adapter (T049) exists; composition-root integration (`create_peer`/`PeerFacade` wiring, settings, provider guide) is not_started |
| T052/T054 kit runtime closure | `accepted` | T052/T054 commits present; kit fixtures pinned and verified |
| T053 kit artifact projection | `not_executed` | only the task/governance packet exists; the 14-artifact kit projection is not implemented |
| T022 K0-K4 / kit matrix | `partial` | kit fixtures and contract tests present; full K0-K4 live runs require explicit `--kit-root` and are not reproduced here |
| Partner provenance / component docs | `accepted` | provenance map present |
| Replay / provider / kit evidence | `accepted` (fixture-level) | replay parity clean; kit vector hashes verified |

## Interop labels

| Label | Verdict |
|---|---|
| `internal_interop` | `accepted` — Replay parity clean, cross-peer replay tests present |
| `kit_interop` | `partial` — fixture/vector conformance proven (K0); production `kit_interop` not yet claimed pending T053 (artifact projection) and live K2/K3/K4 |
| `official_schema` | `blocked` — official templates (INPUT-001) not present; not claimed |

## Accepted head

`EXTERNAL_ACCEPTED_HEAD` (Police) = `7460023ffcc725529288089740a6f692df35b696`

## Branch continuation

The external feature branch `claude/replay-llm-completion-20260823` is open, clean, and its
remote head equals the accepted head. Per the v6 continuation rule, v6 continues this same
feature branch (locally named `lahav-tasks`). No new branch is created. Never commit to
`master`, force-push, rewrite, or auto-merge.

## Residual defects

- Planning-graph check fails (55 issues) — this is the T040 debt to close in v6.
- `config/repo_quality.toml` differs from Thief by design (repo-specific `src/*` paths).
- Full K0-K4 live kit matrix not reproduced (requires explicit `--kit-root` and external kit
  checkout); kit fixture vectors are verified.
- Official schema and live Gmail/counting remain blocked on external inputs (INPUT-001,
  INPUT-003, human authorization).

## v6 dependency impact

- T040 may proceed (planning/line-cap closure).
- T010/T011 may proceed after T040.
- T016 stays blocked (INPUT-001 absent).
- T018/T020 may proceed on their unblocked portions.
- T022 residual must apply the changed-path regression rule using this accepted head.

## Independent review

Independent review (GPT-5.6 Sol) must approve these scope verdicts before the next v6
writer starts. This document records the evidence; approval is a separate gate.