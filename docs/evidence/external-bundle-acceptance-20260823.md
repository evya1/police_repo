# External Bundle Acceptance — Police — 2026-08-23

`M006 — External Bundle Handoff Acceptance`. Maintenance/evidence task.
Requirement IDs: ARCH-008, QR-001, QR-002, QR-004, QR-006, QR-010, QR-011, QR-019, SUB-001.

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
| `uv run python scripts/check_line_cap.py` | 0 | 273 files within 150 lines (5 baselined) |
| `uv run python scripts/check_replay_parity.py --sibling-root ../thief_repo` | 0 | shared_hash_problems: [] |
| `sha256sum vectors/*.json` (kit fixtures) | 0 | all four match pinned PROVENANCE.md hashes |

## External scope verdicts

| Scope | Verdict | Basis |
|---|---|---|
| Governance / M000 / PR truth | `accepted` | ADR-011, provenance map, README/TODO corrections present and coherent |
| T052/T054 kit runtime closure | `accepted` | T052/T054 commits present; kit fixtures pinned and verified |
| Partner provenance / component docs | `accepted` | provenance map present |
| Replay / provider / kit evidence | `accepted` (fixture-level) | replay parity clean; kit vector hashes verified |

## Interop labels

| Label | Verdict |
|---|---|
| `internal_interop` | `accepted` — Replay parity clean, cross-peer replay tests present |

## Accepted head

`EXTERNAL_ACCEPTED_HEAD` (Police) = `7460023ffcc725529288089740a6f692df35b696`

## Branch continuation

The external feature branch `claude/replay-llm-completion-20260823` is open, clean, and its
remote head equals the accepted head. Per the v6 continuation rule, v6 continues this same
feature branch (locally named `lahav-tasks`). No new branch is created. Never commit to
`master`, force-push, rewrite, or auto-merge.
