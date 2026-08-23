"""Trust-level evidence for the replay pipeline (T047, ADR-008): the six outcomes a reader
of a published bundle must be able to tell apart, exercised through the public SDK entry
point end to end (publish -> mutate on disk -> reload -> verify).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from common.domain.scoring import Outcome, Role
from common.transport.canonical import canonical_bytes
from common.transport.replay_evidence import SubgameReplayEvidence
from common.transport.replay_records import decode_half
from common.transport.series import SeriesResult, SeriesRow
from police_peer.reporting import replay_documents as docs
from police_peer.reporting.replay_bundle import publish_replay_bundle
from police_peer.sdk import verify_replay_bundle
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


def _write_and_reseal_manifest(bundle_dir: Path, name: str, data: bytes) -> None:
    """Overwrite one member with ``data`` and recompute the manifest's digest for it —
    the "attacker who also fixes the manifest" step of every scenario below.
    """
    (bundle_dir / name).write_bytes(data)
    manifest_name = docs.member_filename("manifest", GAME_ID)
    manifest = _load(bundle_dir, manifest_name)
    for m in manifest["members"]:
        if m["name"] == name:
            m["sha256"] = hashlib.sha256(data).hexdigest()
    (bundle_dir / manifest_name).write_bytes(docs.serialize_document(manifest))


def test_honest_bundle_is_verified_ok(tmp_path: Path) -> None:
    report = verify_replay_bundle(_bundle(tmp_path))
    assert report.verdict.value == "verified_ok"


def test_one_byte_semantic_mutation_is_tampered(tmp_path: Path) -> None:
    d = _bundle(tmp_path)
    name = docs.member_filename("log", GAME_ID, 1)
    log_doc = _load(d, name)
    log_doc["records"][1]["move"] = "MOVE:W"  # payload changed, stale commit left untouched
    _write_and_reseal_manifest(d, name, docs.serialize_document(log_doc))

    report = verify_replay_bundle(d)
    assert report.verdict.value == "tampered"
    sg = next(sg for sg in report.sub_games if sg.sub_game_index == 1)
    assert any(i.code == "commitment_mismatch" for i in sg.report.issues)


def test_clean_commitment_physics_violation_is_illegal(tmp_path: Path) -> None:
    d = _bundle(tmp_path)
    name = docs.member_filename("log", GAME_ID, 1)
    log_doc = _load(d, name)
    log_doc["records"][1] = reseal({**log_doc["records"][1], "state": "grid=7x7;self=[9, 9];barriers=[]"})
    _write_and_reseal_manifest(d, name, docs.serialize_document(log_doc))

    report = verify_replay_bundle(d)
    assert report.verdict.value == "illegal"
    sg = next(sg for sg in report.sub_games if sg.sub_game_index == 1)
    assert all(i.code != "commitment_mismatch" for i in sg.report.issues)


def test_malformed_json_member_is_invalid(tmp_path: Path) -> None:
    d = _bundle(tmp_path)
    name = docs.member_filename("log", GAME_ID, 1)
    _write_and_reseal_manifest(d, name, b"{not valid json")

    report = verify_replay_bundle(d)
    assert report.verdict.value == "invalid"


def test_missing_member_is_incomplete(tmp_path: Path) -> None:
    d = _bundle(tmp_path)
    (d / docs.member_filename("log", GAME_ID, 6)).unlink()

    report = verify_replay_bundle(d)
    assert report.verdict.value == "incomplete"


def test_recomputed_unanchored_bundle_verifies_but_is_never_authentic(tmp_path: Path) -> None:
    """Payload, nonce, commit, and manifest digest all rewritten consistently for a benign
    field: the bundle is internally consistent (VERIFIED_OK) but must still never be
    described as externally authentic (ADR-008) — this is the whole point of the flag.
    """
    d = _bundle(tmp_path)
    name = docs.member_filename("log", GAME_ID, 1)
    log_doc = _load(d, name)
    log_doc["records"][1] = reseal({**log_doc["records"][1], "hint": "a different but legal hint"})
    _write_and_reseal_manifest(d, name, docs.serialize_document(log_doc))

    report = verify_replay_bundle(d)
    assert report.verdict.value == "verified_ok"
    assert report.coverage.bundle_digests is True
    assert report.coverage.external_authenticity is False
    text = report.to_human().lower()
    assert "unanchored" in text and "never reported as externally authentic" in text
