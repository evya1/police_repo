"""All-or-nothing directory publication (extracted from ADR-009's replay bundle, RP-07).

The mechanics are the bundle's, unchanged: serialize every member in memory, write them into a
unique sibling staging directory, self-verify by reloading what was actually written, and only
then rename once into place under an ``O_EXCL`` publication lock. Any failure leaves no
destination directory and no staging residue.

A stale lock is REPORTED, never deleted. Deleting it is exactly how the race it prevents would
be reintroduced, and a publisher that quietly steals another's lock is worse than one that
stops and says so.

This module knows nothing about artifact schemas. It was lifted out of ``replay_bundle.py`` so
the kit projection could reuse it rather than grow a second implementation of the same careful
sequence -- two of these would drift, and the one that drifted would be the one holding
evidence.
"""

from __future__ import annotations

import os
import secrets
import shutil
from collections.abc import Callable
from pathlib import Path

Checkpoint = Callable[[str], None]
SelfVerify = Callable[[Path], None]


class AtomicPublishError(Exception):
    """Base error for a failed or refused publication."""


class DestinationExistsError(AtomicPublishError):
    """The destination directory already exists; it is never overwritten."""


class PublicationLockError(AtomicPublishError):
    """The O_EXCL publication lock is already held (concurrent publisher or stale lock)."""


class SelfVerifyError(AtomicPublishError):
    """Reloading the staged directory did not self-verify; nothing is published."""


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


def _acquire_lock(lock_path: Path) -> int:
    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise PublicationLockError(f"publication lock already held: {lock_path}") from exc
    os.write(fd, f"pid={os.getpid()}\n".encode())
    return fd


def publish_atomic(
    parent: Path | str,
    name: str,
    files: dict[str, bytes],
    self_verify: SelfVerify,
    *,
    on_checkpoint: Checkpoint | None = None,
) -> Path:
    """Publish ``files`` as ``<parent>/<name>/``, atomically or not at all."""
    parent = Path(parent)
    dest = parent / name
    if dest.exists():
        raise DestinationExistsError(f"destination already exists: {dest}")

    parent.mkdir(parents=True, exist_ok=True)
    staging = parent / f".{name}.staging-{secrets.token_hex(8)}"
    os.mkdir(staging, 0o700)
    os.chmod(staging, 0o700)

    lock_path = parent / f".{name}.publish.lock"
    lock_fd: int | None = None
    published = False
    try:
        for member, data in files.items():
            _write_member(staging, member, data, on_checkpoint)
        _fsync_dir(staging)
        _call(on_checkpoint, "after_stage_fsync")

        self_verify(staging)
        _call(on_checkpoint, "after_self_verify")

        lock_fd = _acquire_lock(lock_path)
        _call(on_checkpoint, "after_lock")
        if dest.exists():
            raise DestinationExistsError(f"destination already exists: {dest}")

        _call(on_checkpoint, "before_publish")
        os.rename(staging, dest)
        published = True
        _fsync_dir(parent)

        os.close(lock_fd)
        lock_fd = None
        os.remove(lock_path)
        return dest
    finally:
        if lock_fd is not None:
            os.close(lock_fd)  # publish failed after acquiring the lock: leave it -- T022 recovery
        if not published and staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
