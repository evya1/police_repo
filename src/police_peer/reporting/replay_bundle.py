"""Atomic, race-safe publication of an internal-interop replay bundle (ADR-009, RP-07).

Publication is all-or-nothing: every document is serialized in memory first (see
``replay_documents.py``), written into a unique sibling staging directory, self-verified
by reloading it and re-running ``verify_replay``, and only then renamed once into place
under an ``O_EXCL`` publication lock. Any failure -- an injected one or a real one -- leaves
no destination directory and no staging residue; a stale lock is reported, never deleted
(that deletion is exactly how the race would be reintroduced -- T022 owns recovery).

The mechanics themselves now live in ``common.transport.atomic_publish``, extracted verbatim
so the kit projection (ADR-012) reuses them instead of growing a second copy. The exception
names below are re-exported aliases: every existing caller, test and except-clause keeps
working, and there is still exactly one implementation of the sequence.
"""

from __future__ import annotations

import json
from pathlib import Path

from common.transport.atomic_publish import (
    AtomicPublishError,
    Checkpoint,
    DestinationExistsError,
    PublicationLockError,
    SelfVerifyError,
    publish_atomic,
)
from common.transport.replay import verify_replay
from common.transport.replay_types import ReplayVerdict
from common.transport.series import SeriesResult
from police_peer.reporting import replay_documents as docs

#: Historical names, kept so no caller or test has to learn a new vocabulary for the same faults.
ReplayBundleError = AtomicPublishError
ReplayBundleExistsError = DestinationExistsError
ReplaySelfVerifyError = SelfVerifyError

__all__ = [
    "Checkpoint", "PublicationLockError", "ReplayBundleError", "ReplayBundleExistsError",
    "ReplaySelfVerifyError", "publish_replay_bundle",
]


def _reload(staging: Path, name: str) -> dict:
    return json.loads((staging / name).read_text(encoding="utf-8"))


def _self_verify(staging: Path, game_id: str) -> None:
    """Reload every config/log pair and re-check it; block only on writer-caused defects.

    ``TAMPERED``/``ILLEGAL`` are legitimate, documented verdicts (RP-04) describing what a
    peer actually did -- they must not block publication. ``INVALID``/``INCOMPLETE`` mean
    *our own* serialization is structurally broken, and must.
    """
    manifest_doc = _reload(staging, docs.member_filename("manifest", game_id))
    log_docs: dict[int, dict] = {}
    issues: list[str] = []
    for index in range(1, docs.SUB_GAME_COUNT + 1):
        config_doc = _reload(staging, docs.member_filename("config", game_id, index))
        log_doc = _reload(staging, docs.member_filename("log", game_id, index))
        log_docs[index] = log_doc
        report = verify_replay(log_doc, config_doc)
        if report.verdict in (ReplayVerdict.INVALID, ReplayVerdict.INCOMPLETE):
            messages = [i.message for i in report.issues]
            issues.append(f"sub_game {index}: {report.verdict.value}: {messages}")
    issues.extend(docs.check_completeness(manifest_doc, log_docs))
    if issues:
        raise ReplaySelfVerifyError("; ".join(issues))


def publish_replay_bundle(
    artifact_root: Path | str,
    result: SeriesResult,
    *,
    on_checkpoint: Checkpoint | None = None,
) -> Path:
    """Publish one internal-interop replay bundle at ``<root>/replay/<game_uid>/``.

    Builds every document in memory, stages it, self-verifies it, then publishes it under
    an O_EXCL lock with a single rename. Raises a ``ReplayBundleError`` subclass and leaves
    no destination directory or staging residue on any failure.
    """
    files = docs.build_all_documents(result)  # pure; raises before any I/O if malformed
    return publish_atomic(
        Path(artifact_root) / "replay",
        result.game_uid,
        files,
        lambda staging: _self_verify(staging, result.game_id),
        on_checkpoint=on_checkpoint,
    )
