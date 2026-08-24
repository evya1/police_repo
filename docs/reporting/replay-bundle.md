# Replay publication (`replay_bundle.py`)

This module publishes the 15 internal replay documents under `<artifact_root>/replay/<game_uid>/`. It serializes first, stages files in a mode-`0700` sibling directory, reloads every config/log, runs `verify_replay`, checks manifest completeness, and publishes with a single rename under an exclusive lock.

## Public API and exceptions

The module re-exports `Checkpoint = Callable[[str], None]` and `PublicationLockError`. Historical aliases preserve the public API:

- `ReplayBundleError` aliases `AtomicPublishError`.
- `ReplayBundleExistsError = DestinationExistsError`
- `ReplaySelfVerifyError = SelfVerifyError`

`publish_replay_bundle(artifact_root: Path | str, result: common.transport.series.SeriesResult, *, on_checkpoint: Checkpoint | None = None) -> Path` builds all documents before I/O and returns `<artifact_root>/replay/<game_uid>` on success.

The parent directory is created if needed. An existing destination raises `ReplayBundleExistsError` and is never overwritten or appended. Invalid/incomplete reloaded replay results or completeness mismatches raise `ReplaySelfVerifyError`; `TAMPERED` and `ILLEGAL` replay verdicts are evidence outcomes and do not block publication. A concurrent or stale `.publish.lock` raises `PublicationLockError` and is not deleted. JSON, verification, filesystem, and checkpoint-hook exceptions otherwise propagate.

Once the publisher enters its cleanup-protected block, unpublished staging is removed on failure. Directory creation and its initial `chmod` occur just before that block, so a failure in the permission setup itself can leave the newly created staging directory. If failure occurs after lock acquisition, the lock intentionally remains for recovery. After the staging directory has been renamed, it is considered published and is not rolled back if later parent-sync or lock-removal work fails. Checkpoint hooks receive `after_write:<name>`, `after_fsync:<name>`, `after_stage_fsync`, `after_self_verify`, `after_lock`, and `before_publish`; hook exceptions are not caught.

Private `_reload` reads one staged JSON file. `_self_verify` requires manifest and config/log files for indices 1 through 6, verifies each pair, then compares record counts/final steps.

## Minimal example

```python
from pathlib import Path
from police_peer.reporting.replay_bundle import publish_replay_bundle

# `result` is a completed common.transport.series.SeriesResult.
destination = publish_replay_bundle(Path("artifacts"), result)
print(destination)  # artifacts/replay/<game_uid>
```

Call only once per `game_uid`; repeat publication is deliberately rejected.
