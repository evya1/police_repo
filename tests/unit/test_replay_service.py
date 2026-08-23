"""Unit tests for the replay application service (T047): membership, digests, pairing,
RP-12 counts, and ``BundleReplayReport`` aggregation/coverage. No CLI, no argparse.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from common.domain.scoring import Outcome, Role
from common.transport.canonical import canonical_bytes
from common.transport.replay_evidence import SubgameReplayEvidence
from common.transport.replay_records import decode_half
from common.transport.replay_types import ReplayVerdict
from common.transport.series import SeriesResult, SeriesRow
from police_peer.replay_service import ReplayServiceError, verify_bundle
from police_peer.reporting import replay_documents as docs
from police_peer.reporting.replay_bundle import publish_replay_bundle
from tests.unit.transport.replay_fixtures import GAME_ID, GAME_UID, TERMS, honest_steps, reseal


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


def _bundle(tmp_path: Path) -> Path:
    entries = tuple(_evidence(i) for i in range(1, 7))
    result = SeriesResult(
        game_id=GAME_ID, game_uid=GAME_UID, ledger=[e.row for e in entries],
        settled=True, settled_outcome=Outcome.CAPTURE, replay_evidence=entries,
    )
    return publish_replay_bundle(tmp_path, result)


def _load(bundle_dir: Path, name: str) -> dict:
    return json.loads((bundle_dir / name).read_text("utf-8"))


def _write(bundle_dir: Path, name: str, doc: dict, *, fix_manifest: bool = True) -> None:
    data = docs.serialize_document(doc)
    (bundle_dir / name).write_bytes(data)
    if fix_manifest:
        manifest_name = docs.member_filename("manifest", GAME_ID)
        manifest = _load(bundle_dir, manifest_name)
        for m in manifest["members"]:
            if m["name"] == name:
                m["sha256"] = hashlib.sha256(data).hexdigest()
        (bundle_dir / manifest_name).write_bytes(docs.serialize_document(manifest))


def test_honest_bundle_verified_ok_with_digests_checked(tmp_path: Path) -> None:
    report = verify_bundle(_bundle(tmp_path))
    assert report.verdict == ReplayVerdict.VERIFIED_OK
    assert (report.coverage.bundle_digests, report.coverage.external_authenticity) == (True, False)
    assert len(report.sub_games) == 6 and report.checked_records == 24


def test_missing_directory_is_a_path_usage_error(tmp_path: Path) -> None:
    with pytest.raises(ReplayServiceError):
        verify_bundle(tmp_path / "nope")


def test_no_manifest_is_invalid(tmp_path: Path) -> None:
    d = _bundle(tmp_path)
    (d / docs.member_filename("manifest", GAME_ID)).unlink()
    assert verify_bundle(d).verdict == ReplayVerdict.INVALID


def test_uid_directory_name_mismatch_is_invalid(tmp_path: Path) -> None:
    d = _bundle(tmp_path)
    wrong = d.rename(d.parent / "not-the-uid")
    assert verify_bundle(wrong).verdict == ReplayVerdict.INVALID


def test_unexpected_extra_member_is_invalid(tmp_path: Path) -> None:
    d = _bundle(tmp_path)
    (d / "extra.json").write_text("{}", encoding="utf-8")
    report = verify_bundle(d)
    assert report.verdict == ReplayVerdict.INVALID
    assert any("extra member" in i for i in report.issues)


def test_missing_expected_member_is_incomplete(tmp_path: Path) -> None:
    d = _bundle(tmp_path)
    (d / docs.member_filename("log", GAME_ID, 3)).unlink()
    report = verify_bundle(d)
    assert report.verdict == ReplayVerdict.INCOMPLETE
    assert any("missing member" in i for i in report.issues)


def test_digest_mismatch_against_manifest_is_tampered(tmp_path: Path) -> None:
    d = _bundle(tmp_path)
    name = docs.member_filename("log", GAME_ID, 2)
    (d / name).write_bytes((d / name).read_bytes() + b" ")
    report = verify_bundle(d)
    assert report.verdict == ReplayVerdict.TAMPERED
    assert any("digest mismatch" in i for i in report.issues)


def test_zero_matching_configs_never_succeeds(tmp_path: Path) -> None:
    d = _bundle(tmp_path)
    name = docs.member_filename("log", GAME_ID, 4)
    log_doc = _load(d, name)
    log_doc["game_id"] = "different-game"
    _write(d, name, log_doc)
    report = verify_bundle(d)
    assert report.verdict != ReplayVerdict.VERIFIED_OK
    assert any("found 0 matching configs" in i for i in report.issues)


def test_multiple_matching_configs_never_succeeds(tmp_path: Path) -> None:
    d = _bundle(tmp_path)
    cfg1_name = docs.member_filename("config", GAME_ID, 1)
    cfg2_name = docs.member_filename("config", GAME_ID, 2)
    cfg1, cfg2 = _load(d, cfg1_name), _load(d, cfg2_name)
    cfg2["sub_game_index"], cfg2["game_id"], cfg2["game_uid"] = 1, cfg1["game_id"], cfg1["game_uid"]
    _write(d, cfg2_name, cfg2)
    report = verify_bundle(d)
    assert report.verdict != ReplayVerdict.VERIFIED_OK
    assert any("found 2 matching configs" in i for i in report.issues)


def test_manifest_count_mismatch_is_rp12_incomplete(tmp_path: Path) -> None:
    d = _bundle(tmp_path)
    manifest_name = docs.member_filename("manifest", GAME_ID)
    manifest = _load(d, manifest_name)
    next(sg for sg in manifest["sub_games"] if sg["sub_game_index"] == 5)["own_record_count"] = 999
    _write(d, manifest_name, manifest)
    report = verify_bundle(d)
    assert report.verdict == ReplayVerdict.INCOMPLETE
    assert all(sg.report.verdict == ReplayVerdict.VERIFIED_OK for sg in report.sub_games)
    assert any("record count" in i for i in report.issues)


def test_tampered_subgame_outranks_illegal_subgame(tmp_path: Path) -> None:
    d = _bundle(tmp_path)
    name1 = docs.member_filename("log", GAME_ID, 1)
    log1 = _load(d, name1)
    log1["records"][1] = reseal({**log1["records"][1], "state": "grid=7x7;self=[9, 9];barriers=[]"})
    _write(d, name1, log1)

    name2 = docs.member_filename("log", GAME_ID, 2)
    log2 = _load(d, name2)
    log2["records"][1]["move"] = "MOVE:W"  # stale commit left untouched
    _write(d, name2, log2)

    report = verify_bundle(d)
    by_index = {sg.sub_game_index: sg.report.verdict for sg in report.sub_games}
    assert report.verdict == ReplayVerdict.TAMPERED
    assert (by_index[1], by_index[2]) == (ReplayVerdict.ILLEGAL, ReplayVerdict.TAMPERED)


def test_to_json_shape(tmp_path: Path) -> None:
    d = verify_bundle(_bundle(tmp_path)).to_json()
    assert set(d) == {"game_id", "game_uid", "verdict", "coverage", "checked_records", "sub_games", "issues"}
    assert len(d["sub_games"]) == 6


def test_to_human_states_unanchored_never_authentic(tmp_path: Path) -> None:
    text = verify_bundle(_bundle(tmp_path)).to_human()
    assert "unanchored" in text.lower() and "VERIFIED_OK" in text
