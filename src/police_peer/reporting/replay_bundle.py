"""Atomic, race-safe publication of an internal-interop replay bundle (ADR-009, RP-07).

Publication is all-or-nothing: every document is serialized in memory first (see
``replay_documents.py``), written into a unique sibling staging directory, self-verified
by reloading it and re-running ``verify_replay``, and only then renamed once into place
under an ``O_EXCL`` publication lock. Any failure — an injected one or a real one — leaves
no destination directory and no staging residue; a stale lock is reported, never deleted
(that deletion is exactly how the race would be reintroduced — T022 owns recovery).
"""

from __future__ import annotations

import json
import os
import secrets
import shutil
from collections.abc import Callable
from pathlib import Path

from common.transport.replay import verify_replay
from common.transport.replay_types import ReplayVerdict
from common.transport.series import SeriesResult
from police_peer.reporting import replay_documents as docs

Checkpoint = Callable[[str], None]


class ReplayBundleError(Exception):
    """Base error for a failed or refused replay-bundle publication."""


class ReplayBundleExistsError(ReplayBundleError):
    """The destination UID directory already exists; it is never overwritten."""


class PublicationLockError(ReplayBundleError):
    """The O_EXCL publication lock is already held (concurrent publisher or stale lock)."""


class ReplaySelfVerifyError(ReplayBundleError):
    """Reloading the staged bundle did not self-verify; nothing is published."""


def _call(hook: Checkpoint | None, checkpoint: str) -> None:
    if hook is not None:
        hook(checkpoint)


def _fsync_dir(path: Path) -> None:
    """Fsync a directory where the platform supports it; a no-op capability gap otherwise."""
    if not hasattr(os, "O_DIRECTORY"):
        return  # e.g. Windows has no directory file descriptor to fsync
    fd = os.open(path, os.O_DIRECTORY)
    try:
        os.fsync(fd)
    except OSError:
        pass  # some filesystems reject directory fsync; the file-level fsyncs already ran
    finally:
        os.close(fd)


def _write_member(staging: Path, name: str, data: bytes, hook: Checkpoint | None) -> None:
    with open(staging / name, "wb") as handle:
        handle.write(data)
        handle.flush()
        _call(hook, f"after_write:{name}")
        os.fsync(handle.fileno())
        _call(hook, f"after_fsync:{name}")


def _reload(staging: Path, name: str) -> dict:
    return json.loads((staging / name).read_text(encoding="utf-8"))


def _self_verify(staging: Path, game_id: str) -> None:
    """Reload every config/log pair and re-check it; block only on writer-caused defects.

    ``TAMPERED``/``ILLEGAL`` are legitimate, documented verdicts (RP-04) describing what a
    peer actually did — they must not block publication. ``INVALID``/``INCOMPLETE`` mean
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


def _acquire_lock(lock_path: Path) -> int:
    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise PublicationLockError(f"publication lock already held: {lock_path}") from exc
    os.write(fd, f"pid={os.getpid()}\n".encode())
    return fd


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
    replay_root = Path(artifact_root) / "replay"
    dest = replay_root / result.game_uid
    if dest.exists():
        raise ReplayBundleExistsError(f"replay bundle already exists: {dest}")

    replay_root.mkdir(parents=True, exist_ok=True)
    staging = replay_root / f".{result.game_uid}.staging-{secrets.token_hex(8)}"
    os.mkdir(staging, 0o700)
    os.chmod(staging, 0o700)

    lock_path = replay_root / f".{result.game_uid}.publish.lock"
    lock_fd: int | None = None
    published = False
    try:
        for name, data in files.items():
            _write_member(staging, name, data, on_checkpoint)
        _fsync_dir(staging)
        _call(on_checkpoint, "after_stage_fsync")

        _self_verify(staging, result.game_id)
        _call(on_checkpoint, "after_self_verify")

        lock_fd = _acquire_lock(lock_path)
        _call(on_checkpoint, "after_lock")
        if dest.exists():
            raise ReplayBundleExistsError(f"replay bundle already exists: {dest}")

        _call(on_checkpoint, "before_publish")
        os.rename(staging, dest)
        published = True
        _fsync_dir(replay_root)

        os.close(lock_fd)
        lock_fd = None
        os.remove(lock_path)
        return dest
    finally:
        if lock_fd is not None:
            os.close(lock_fd)  # publish failed after acquiring the lock: leave it — T022 recovery
        if not published and staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
