---
id: T053
status: not_started
priority: P2
task_type: component
component: C06
optional: true
implements:
  - REPORT-005
  - REPORT-006
  - OBS-006
context_files:
  - docs/components/C06-reporting-league/PRD.md
  - docs/components/C06-reporting-league/PLAN.md
  - docs/interop/LEAGUE_COMPATIBILITY.md
  - docs/decisions/ADR-011-league-kit-interoperability-boundary.md
read_set:
  - src/police_peer/reporting/replay_bundle.py
  - src/police_peer/reporting/replay_documents.py
depends_on:
  - T046
  - T052
gates: []
parallel_safe: true
claimed_by:
claim_expires_at:
write_set:
  - src/police_peer/reporting/league_kit_projection.py
  - tests/unit/reporting/test_league_kit_projection.py
  - tests/integration/test_league_kit_artifact_check.py
risk: medium
---

# T053 — League-kit artifact projection (separate from T046's internal bundle)

## Expected outcome

A settled six-sub-game series can be projected into the pinned `copthief-league-protocol` kit's
four artifact kinds — one declaration, six configs, six logs, one result (14 JSON files) — such
that the kit's own `tools/check_artifacts.py` and `python -m sparring.cli replay --expect-clean`
accept them. This is a second, separate projection of the same settled series T046 already
captures as an internal-interop bundle; it does not replace, rename, or weaken T046.

## Requirements implemented

- `REPORT-005`, `REPORT-006` — artifact generation for external interoperability evidence.
- `OBS-006` — evidence-projection coverage alongside the existing Replay observability path.

## Relevant context

Pinned kit commit `ad6557626587e09146af4283a5e808e7001343c5`
(https://github.com/Imreec/copthief-league-protocol, MIT). See `ADR-011` for the `internal_interop`
/`kit_interop`/`official_schema` status separation this task must respect: every artifact and log
line this task produces is labeled `kit_interop` (or left unlabeled by the kit's own schema,
whichever the kit's own artifact shape expects) — never `official_schema`, and this task never
claims external authenticity on its own.

Filenames follow SPEC §4: `declaration_<game_id>.json`, `config_<game_id>_g<NN>.json`,
`log_<game_id>_g<NN>.json` (six, zero-padded `g01`..`g06`), `result_<game_id>.json` — 14 files
total for a six-sub-game series. A sparring-only marker file such as `NOT_A_LEAGUE_GAME.txt`, if
the kit's own tooling writes one, is not counted among the 14 and is not this task's concern to
produce.

`game_id`/`game_uid` must be the exact same stable identifiers T052's per-sub-game lifecycle work
derives and pins for the series — this task reads them, it does not re-derive them independently
(two independent derivations of the same "shared" identifier is exactly the class of bug SPEC §4
documents as having actually broken a live cross-team match).

## Constraints

- Edit only the declared write set.
- Do not modify `src/police_peer/reporting/replay_bundle.py` or `replay_documents.py` (T046,
  already committed) — this is an additive, separate projection module.
- Deterministic UTF-8 serialization, matching the kit's own canonical-JSON expectations (sorted
  keys, compact separators, `ensure_ascii=False`) — reuse `common/transport/league_kit_envelope.py`
  (T052) for the shared serialization primitive rather than reimplementing it.
- No official-schema or external-authenticity claim anywhere in code, docstrings, or emitted
  artifacts.

## Acceptance criteria

- [ ] For a real settled six-sub-game series, the projection emits exactly 14 JSON files: one
      declaration, six configs, six logs, one result — proven by an explicit count assertion, not
      merely "no exception raised".
- [ ] One stable `game_id` and `game_uid` across all 14 files, read from T052's pinned series
      identity, not independently re-derived.
- [ ] Deterministic UTF-8 serialization: re-running the projection over the same settled series
      produces byte-identical output.
- [ ] `python tools/check_artifacts.py <projection-dir>` (run against the pinned kit checkout)
      accepts an honest projection with exit `0`.
- [ ] `python -m sparring.cli replay <projection-dir> --expect-clean` (pinned kit checkout)
      verifies all six logs clean, zero tampered, exit `0`.
- [ ] Negative-control fixtures (each a separate test, each checked against the kit's own
      checker): one committed payload byte mutated without regenerating its digest → non-zero,
      tamper attribution; content mutated with a correctly regenerated digest → non-zero,
      content-level invalid attribution (never described as tampering); one required
      artifact/member removed → non-zero, incomplete/invalid; `game_uid` changed in one artifact
      → non-zero, join failure; one sub-game result row dropped → non-zero, settlement/count
      mismatch; conflicting peer result artifacts → non-zero, cross-peer disagreement.
- [ ] Every emitted artifact/log statement is labeled `kit_interop`, never `official_schema`, and
      no code path asserts external authenticity.

## Verification

- `uv run pytest tests/unit/reporting/test_league_kit_projection.py tests/integration/test_league_kit_artifact_check.py -v`
- `uv run pytest` (full suite — must remain green)
- `uv run ruff check .`
- `uv run python scripts/check_line_cap.py`
- `python tools/check_artifacts.py <dir>` and `python -m sparring.cli replay <dir> --expect-clean`
  (run inside the pinned kit checkout against a projection this task produced)

## Handoff contract

Report files changed, tests executed, exact results, the exact kit-checker output for both the
honest case and every negative control, decisions, deviations, and blockers.

## Result and evidence

(to be filled)
