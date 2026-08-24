"""The extracted publication sequence must behave exactly as the replay bundle's always did."""

from __future__ import annotations

import os

import pytest

from common.transport.atomic_publish import (
    DestinationExistsError,
    PublicationLockError,
    SelfVerifyError,
    publish_atomic,
)

FILES = {"a.json": b"{}\n", "b.json": b"[]\n"}


def _ok(_staging) -> None:
    return None


def test_publishes_every_member_under_one_directory(tmp_path):
    dest = publish_atomic(tmp_path, "uid-1", FILES, _ok)
    assert dest == tmp_path / "uid-1"
    assert {p.name for p in dest.iterdir()} == set(FILES)
    assert (dest / "a.json").read_bytes() == b"{}\n"


def test_an_existing_destination_is_never_overwritten(tmp_path):
    publish_atomic(tmp_path, "uid-1", FILES, _ok)
    with pytest.raises(DestinationExistsError):
        publish_atomic(tmp_path, "uid-1", FILES, _ok)


def test_a_failed_self_verify_publishes_nothing_and_leaves_no_residue(tmp_path):
    def refuse(_staging):
        raise SelfVerifyError("nope")

    with pytest.raises(SelfVerifyError):
        publish_atomic(tmp_path, "uid-1", FILES, refuse)
    assert not (tmp_path / "uid-1").exists()
    assert not [p for p in tmp_path.iterdir() if p.name.startswith(".uid-1.staging")]


def test_a_held_lock_refuses_and_the_lock_is_left_in_place(tmp_path):
    """A stale lock is reported, never deleted -- stealing it reintroduces the race."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    lock = tmp_path / ".uid-1.publish.lock"
    lock.write_text("pid=999\n")
    with pytest.raises(PublicationLockError):
        publish_atomic(tmp_path, "uid-1", FILES, _ok)
    assert lock.exists(), "the lock must survive a refusal"
    assert not (tmp_path / "uid-1").exists()


def test_the_lock_is_released_on_success(tmp_path):
    publish_atomic(tmp_path, "uid-1", FILES, _ok)
    assert not (tmp_path / ".uid-1.publish.lock").exists()


def test_checkpoints_fire_in_the_documented_order(tmp_path):
    seen: list[str] = []
    publish_atomic(tmp_path, "uid-1", FILES, _ok, on_checkpoint=seen.append)
    for label in ("after_stage_fsync", "after_self_verify", "after_lock", "before_publish"):
        assert label in seen, label
    assert seen.index("after_stage_fsync") < seen.index("after_self_verify")
    assert seen.index("after_self_verify") < seen.index("after_lock")
    assert seen.index("after_lock") < seen.index("before_publish")
    for member in FILES:
        assert seen.index(f"after_write:{member}") < seen.index(f"after_fsync:{member}")
        assert seen.index(f"after_fsync:{member}") < seen.index("after_stage_fsync")


def test_a_failure_injected_at_a_checkpoint_leaves_nothing_behind(tmp_path):
    def boom(label: str) -> None:
        if label == "after_write:a.json":
            raise RuntimeError("injected")

    with pytest.raises(RuntimeError, match="injected"):
        publish_atomic(tmp_path, "uid-1", FILES, _ok, on_checkpoint=boom)
    assert not (tmp_path / "uid-1").exists()
    assert not [p for p in tmp_path.iterdir() if p.name.startswith(".uid-1.staging")]


def test_staging_is_private_while_it_exists(tmp_path):
    modes: list[int] = []

    def peek(label: str) -> None:
        if label == "after_stage_fsync":
            staging = next(p for p in tmp_path.iterdir() if p.name.startswith(".uid-1.staging"))
            modes.append(os.stat(staging).st_mode & 0o777)

    publish_atomic(tmp_path, "uid-1", FILES, _ok, on_checkpoint=peek)
    assert modes == [0o700]
