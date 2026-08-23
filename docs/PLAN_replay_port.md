# PLAN — Replay evidence and offline verification (police_repo)

## Phase 0 — orchestrator-only stabilization

- Pin the branch HEAD and save `git status --short` before edits.
- Keep the existing non-colliding T046/T047 identifiers.
- Replace `docs/PRD_replay_port.md`, `docs/PLAN_replay_port.md`, and `docs/TODO_replay_port.md` with the approved versions from this pack.
- Amend task write sets before claims; the worker may edit only its task packet paths.
- Record ADRs for verdict/coverage taxonomy and internal-interop atomic bundles.
- Mark official-template criteria as blocked by INPUT-001/T016; do not block internal replay implementation.

## Phase 1 — T033 shared replay core

Create/rewrite the pure shared slice:

- `common/transport/replay_types.py` — enums and frozen reports.
- `common/transport/replay_records.py` — strict flat/nested record codecs.
- `common/transport/replay.py` — `verify_replay(log_doc, config_doc) -> ReplayReport`, no filesystem.
- `tests/unit/transport/replay_fixtures.py`
- `tests/unit/transport/test_replay_records.py`
- `tests/unit/transport/test_replay_verify.py`

In Thief this replaces, rather than patches around, the broken first-record foreign-shape branch. Split tests to remain under the line cap. Copy the approved shared result byte-for-byte to the sibling repository and run the same tests there.

## Phase 2 — T034 immutable evidence capture

- Add `common/transport/replay_evidence.py` with frozen `SubgameReplayEvidence` using tuples and canonical bytes, including the opponent commitments captured from `Inbox.played` before the inbox is discarded.
- Change `common/transport/subgame.py` so the subgame driver returns `SubgameReplayEvidence` plus the existing row semantics.
- Change `common/transport/series.py` so `SeriesResult` carries `tuple[SubgameReplayEvidence, ...]`, default empty for source compatibility.
- Add `tests/unit/transport/test_series_replay_evidence.py`.

Preserve live audit ordering, barriers, settlement, and wire messages. Evidence capture is an observation of already-created values, not a new state machine.

## Phase 3 — T046 document building and atomic publish

Per-repository files:

- `src/police_peer/reporting/replay_documents.py` — pure document builders and serializers.
- `src/police_peer/reporting/replay_bundle.py` — staging, manifest, self-verification, atomic rename.
- `src/police_peer/runner.py` — call writer after a settled series; existing summary output remains unchanged.
- unit and integration tests under `tests/unit/reporting/` and `tests/integration/`.

The output path is `<artifact_root>/replay/<game_uid>/`. Build all bytes in memory first. Create a unique sibling staging directory with mode 0700, write exact files, flush and fsync files/staging where supported, validate manifest and replay reports, acquire an O_EXCL publication lock, rename once, then fsync the parent where supported. A second publisher fails closed. Cleanup staging in `finally`; a stale lock is reported for T022 recovery, never silently deleted.

## Phase 4 — T047 use case, CLI, and evidence

- `src/police_peer/replay_service.py` loads exactly one UID directory, validates manifest membership/digests, pairs configs/logs by identity, and calls the pure verifier.
- `src/police_peer/sdk.py` exports `verify_replay_bundle(path) -> BundleReplayReport`.
- `scripts/replay.py` maps report to stable human/JSON output and exit codes: 0 verified, 4 illegal, 5 invalid/incomplete, 6 tampered, 2 usage/path error.
- `scripts/smoke_replay_integration.py` exercises public SDK -> loopback series -> bundle -> verifier.
- `scripts/check_replay_parity.py` compares shared bytes and invokes sibling CLIs as subprocesses; it never imports the sibling.
- Integration tests create an honest bundle, mutate a copied payload byte, and test all exit classes.

## Phase 5 — cross-repo final gate

Run both full suites independently. Compare shared files by SHA-256 and `diff -rq`. Exercise a Police-created frozen bundle with Thief's CLI and vice versa in separate subprocess working directories. The orchestrator reviews every changed file and evidence transcript before board status changes.

## Dependency graph

`T033 -> T034 -> T046 -> T047`. T033 may be implemented once then statically ported. T015 GUI depends on T047. T016 official schemas remain separately gated.
