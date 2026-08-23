---
id: T046
status: not_started
priority: P0
task_type: component
component: C06
optional: false
implements:
  - REPORT-005
  - REPORT-006
  - REPORT-007
  - REPORT-008
  - REPORT-009
  - OBS-006
context_files:
  - docs/components/C06-reporting-league/PRD.md
  - docs/components/C06-reporting-league/PLAN.md
  - docs/PRD_replay_port.md
  - docs/PLAN_replay_port.md
read_set: []
depends_on:
  - T033
  - T034
gates:
  - id: INPUT-001
    kind: input
    scope: official_templates
    blocks: criterion
parallel_safe: true
claimed_by:
claim_expires_at:
write_set:
  - src/police_peer/reporting/replay_documents.py
  - src/police_peer/reporting/replay_bundle.py
  - src/police_peer/runner.py
  - tests/unit/reporting/test_replay_documents.py
  - tests/unit/reporting/test_replay_bundle.py
  - tests/integration/test_replay_bundle_publish.py
  - tests/integration/test_replay_bundle_concurrency.py
risk: medium
---

# T046 — Internal-interop documents and atomic replay bundle

## Expected outcome

After a settled series the runner publishes exactly one complete replay bundle at
`<artifact_root>/replay/<game_uid>/`, or publishes nothing at all. Every emitted document is
explicitly labelled `internal_interop`; nothing is described as official.

## Requirements implemented

- `REPORT-005`
- `REPORT-006`
- `REPORT-007`
- `REPORT-008`
- `REPORT-009`
- `OBS-006`

## Relevant context

Implements RP-03, RP-07, RP-08, and RP-12 of `docs/PRD_replay_port.md`. REVIEW_FINDINGS F-10: artifact
writes are independent `write_text` calls, so a crash or cancellation can leave a partially
valid-looking bundle. F-11: the official templates are absent, so a guessed official schema would
create false compliance.

## Gates

- `INPUT-001` (`input`, `blocks: criterion`) — only the official-schema acceptance criterion waits.
  Internal-interop implementation is not blocked. `{#official_templates}`

## Constraints

- Edit only the declared write set. Do **not** extend `reporting/pipeline.py` and do not replace the
  existing result summary output.
- Build every byte in memory first, then stage, then publish.
- Never overwrite an existing UID directory; an existing destination fails closed.
- Every code and test file stays below 150 logical lines.
- No guessed official schema, no DI framework, Repository/Unit of Work, or event bus.

## Acceptance criteria

- [ ] Pure builders emit deterministic declaration, config, log, result, and manifest dictionaries.
      All carry `schema_version`, `artifact_kind`, `schema_status: internal_interop`, non-empty
      `game_uid` and `game_id`, config/log pairs carry the same `sub_game_index`, and cross-document
      expected record counts and final steps agree for both halves (RP-12), so a truncated final
      record cannot pass merely because the remaining sequence is contiguous.
- [ ] Serialization is UTF-8 with stable key ordering and a trailing newline.
- [ ] The writer creates `<root>/replay/.<uid>.staging-<random>` with mode 0700, writes the exact
      member set, flushes and **fsyncs** files and the staging directory where supported, computes
      digests, reloads and self-verifies all six config/log pairs, acquires an **O_EXCL publication
      lock**, renames once, and fsyncs the parent directory where supported.
- [ ] The manifest lists exact member names and SHA-256 file digests: one declaration, six configs,
      six non-empty logs, one result.
- [ ] Failure injected after each individual write, after fsync, and at publish leaves no destination
      directory and no staging residue; cleanup happens in `finally`.
- [ ] An existing destination is never overwritten, and a stale publication lock is reported for
      T022 recovery rather than silently deleted.
- [ ] Two concurrent publishers race for the same UID: exactly one wins, the loser fails closed, and
      the winner's bundle is never overwritten or partially observed.
- [ ] Integration test publishes a bundle from a real settled series and verifies exact counts,
      digests, and identity.
- [ ] No document claims official-schema compliance while `INPUT-001` is unresolved.
      `{#official_templates}`

## Verification

- `uv run pytest tests/unit/reporting/test_replay_documents.py tests/unit/reporting/test_replay_bundle.py tests/integration/test_replay_bundle_publish.py tests/integration/test_replay_bundle_concurrency.py`
- `uv run ruff check src/police_peer/reporting src/police_peer/runner.py tests`
- `uv run python scripts/check_line_cap.py`

## Result and evidence

(to be filled)
