"""Unit tests for atomic publication mechanics (T046, ADR-009): staging, self-verify,
lock, rename, and failure-injection cleanup — using tmp_path, no live game required.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from common.domain.scoring import Outcome, Role
from common.transport.canonical import canonical_bytes
from common.transport.replay_evidence import SubgameReplayEvidence
from common.transport.replay_records import decode_half
from common.transport.series import SeriesResult, SeriesRow
from police_peer.reporting import replay_bundle as bundle
from tests.unit.transport.replay_fixtures import GAME_ID, GAME_UID, TERMS, honest_steps


def _own(n: int = 3) -> tuple:
    records, issues = decode_half(honest_steps(n), "own")
    assert not issues
    return tuple(records)


def _evidence(index: int) -> SubgameReplayEvidence:
    return SubgameReplayEvidence(
        sub_game_index=index, terms_bytes=canonical_bytes(TERMS), own_records=_own(3),
        opponent_records=(), observed_opponent_commitments=(), our_result_claim="capture",
        opponent_result_claim=None, row=SeriesRow(index, Role.THIEF, Outcome.CAPTURE, 3, 0, 1, True),
        game_id=GAME_ID, game_uid=GAME_UID,
    )


def _result() -> SeriesResult:
    entries = tuple(_evidence(i) for i in range(1, 7))
    return SeriesResult(
        game_id=GAME_ID, game_uid=GAME_UID, ledger=[e.row for e in entries],
        settled=True, settled_outcome=Outcome.CAPTURE, replay_evidence=entries,
    )


def _no_residue(root: Path, uid: str) -> None:
    replay_root = root / "replay"
    assert not (replay_root / uid).exists()
    if replay_root.exists():
        assert not any(p.name.startswith(f".{uid}.staging-") for p in replay_root.iterdir())


class TestSuccessfulPublish:
    def test_publishes_exact_directory_with_mode_0700_staging(self, tmp_path: Path) -> None:
        seen: list[str] = []
        dest = bundle.publish_replay_bundle(tmp_path, _result(), on_checkpoint=seen.append)
        assert dest == tmp_path / "replay" / GAME_UID
        assert dest.is_dir()
        assert len(list(dest.iterdir())) == 15
        assert any(cp.startswith("after_write:") for cp in seen)
        assert "before_publish" in seen

    def test_lock_file_removed_after_success_no_staging_residue(self, tmp_path: Path) -> None:
        bundle.publish_replay_bundle(tmp_path, _result())
        replay_root = tmp_path / "replay"
        assert not (replay_root / f".{GAME_UID}.publish.lock").exists()
        assert not any(p.name.startswith(f".{GAME_UID}.staging-") for p in replay_root.iterdir())


class TestExistingDestinationNeverOverwritten:
    def test_second_publish_of_same_uid_fails_closed(self, tmp_path: Path) -> None:
        bundle.publish_replay_bundle(tmp_path, _result())
        before = sorted((tmp_path / "replay" / GAME_UID).iterdir())
        with pytest.raises(bundle.ReplayBundleExistsError):
            bundle.publish_replay_bundle(tmp_path, _result())
        assert sorted((tmp_path / "replay" / GAME_UID).iterdir()) == before


class TestStaleLockReportedNotDeleted:
    def test_pre_existing_lock_reported_and_left_in_place(self, tmp_path: Path) -> None:
        replay_root = tmp_path / "replay"
        replay_root.mkdir(parents=True)
        lock_path = replay_root / f".{GAME_UID}.publish.lock"
        lock_path.write_text("pid=stale\n", encoding="utf-8")
        with pytest.raises(bundle.PublicationLockError):
            bundle.publish_replay_bundle(tmp_path, _result())
        assert lock_path.exists()  # never silently deleted — T022 owns recovery
        assert lock_path.read_text(encoding="utf-8") == "pid=stale\n"
        _no_residue(tmp_path, GAME_UID)


class TestFailureInjectionLeavesNoResidue:
    @pytest.mark.parametrize(
        "checkpoint",
        [
            "after_write:manifest_A-vs-B.json",
            "after_stage_fsync",
            "after_self_verify",
            "before_publish",
        ],
    )
    def test_injected_failure_leaves_no_destination_or_staging(
        self, tmp_path: Path, checkpoint: str
    ) -> None:
        def hook(cp: str) -> None:
            if cp == checkpoint:
                raise RuntimeError(f"injected at {cp}")

        with pytest.raises(RuntimeError, match="injected"):
            bundle.publish_replay_bundle(tmp_path, _result(), on_checkpoint=hook)
        _no_residue(tmp_path, GAME_UID)

    def test_failure_after_lock_leaves_lock_but_no_staging(self, tmp_path: Path) -> None:
        def hook(cp: str) -> None:
            if cp == "after_lock":
                raise RuntimeError("injected at after_lock")

        with pytest.raises(RuntimeError, match="injected"):
            bundle.publish_replay_bundle(tmp_path, _result(), on_checkpoint=hook)
        lock_path = tmp_path / "replay" / f".{GAME_UID}.publish.lock"
        assert lock_path.exists()  # stale lock left for T022, not cleaned by us
        assert not (tmp_path / "replay" / GAME_UID).exists()
        replay_root = tmp_path / "replay"
        assert not any(p.name.startswith(f".{GAME_UID}.staging-") for p in replay_root.iterdir())


def test_staging_directory_created_with_mode_0700(tmp_path: Path) -> None:
    modes: list[int] = []

    def hook(cp: str) -> None:
        if cp.startswith("after_write:") and not modes:
            staging = next((tmp_path / "replay").glob(f".{GAME_UID}.staging-*"))
            modes.append(stat.S_IMODE(os.stat(staging).st_mode))

    bundle.publish_replay_bundle(tmp_path, _result(), on_checkpoint=hook)
    if os.name != "nt":
        assert modes == [0o700]
