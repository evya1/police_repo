"""Integration: the headless replay CLI as a real subprocess (T047) — exit codes,
``--json`` output shape, and the path/usage error case.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

from common.domain.scoring import Outcome, Role
from common.transport.canonical import canonical_bytes
from common.transport.replay_evidence import SubgameReplayEvidence
from common.transport.replay_records import decode_half
from common.transport.series import SeriesResult, SeriesRow
from police_peer.reporting import replay_documents as docs
from police_peer.reporting.replay_bundle import publish_replay_bundle
from tests.unit.transport.replay_fixtures import GAME_ID, GAME_UID, TERMS, honest_steps, reseal

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CLI = _REPO_ROOT / "scripts" / "replay.py"


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


def _write(bundle_dir: Path, name: str, doc: dict) -> None:
    data = docs.serialize_document(doc)
    (bundle_dir / name).write_bytes(data)
    manifest_name = docs.member_filename("manifest", GAME_ID)
    manifest = json.loads((bundle_dir / manifest_name).read_text("utf-8"))
    for m in manifest["members"]:
        if m["name"] == name:
            m["sha256"] = hashlib.sha256(data).hexdigest()
    (bundle_dir / manifest_name).write_bytes(docs.serialize_document(manifest))


def _run_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(_CLI), *args], cwd=_REPO_ROOT, capture_output=True, text=True, check=False
    )


def test_honest_bundle_exits_zero_human_readable(tmp_path: Path) -> None:
    proc = _run_cli(str(_bundle(tmp_path)))
    assert proc.returncode == 0
    assert "VERIFIED_OK" in proc.stdout
    assert "external_authenticity=False" in proc.stdout


def test_honest_bundle_json_flag_is_valid_json(tmp_path: Path) -> None:
    proc = _run_cli(str(_bundle(tmp_path)), "--json")
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["verdict"] == "verified_ok"
    assert payload["coverage"]["external_authenticity"] is False
    assert len(payload["sub_games"]) == 6


def test_digest_tampered_bundle_exits_six(tmp_path: Path) -> None:
    d = _bundle(tmp_path)
    name = docs.member_filename("log", GAME_ID, 1)
    (d / name).write_bytes((d / name).read_bytes() + b" ")
    proc = _run_cli(str(d), "--json")
    assert proc.returncode == 6
    assert json.loads(proc.stdout)["verdict"] == "tampered"


def test_missing_member_bundle_exits_five(tmp_path: Path) -> None:
    d = _bundle(tmp_path)
    (d / docs.member_filename("log", GAME_ID, 2)).unlink()
    proc = _run_cli(str(d), "--json")
    assert proc.returncode == 5
    assert json.loads(proc.stdout)["verdict"] == "incomplete"


def test_missing_path_exits_two(tmp_path: Path) -> None:
    proc = _run_cli(str(tmp_path / "does-not-exist"))
    assert proc.returncode == 2
    assert proc.stdout == ""
    assert "error:" in proc.stderr


def test_clean_commitment_illegal_move_exits_four(tmp_path: Path) -> None:
    d = _bundle(tmp_path)
    name = docs.member_filename("log", GAME_ID, 3)
    log_doc = json.loads((d / name).read_text("utf-8"))
    log_doc["records"][1] = reseal({**log_doc["records"][1], "state": "grid=7x7;self=[9, 9];barriers=[]"})
    _write(d, name, log_doc)
    proc = _run_cli(str(d), "--json")
    assert proc.returncode == 4
    payload = json.loads(proc.stdout)
    assert payload["verdict"] == "illegal"
    assert not any(i["code"] == "commitment_mismatch" for sg in payload["sub_games"] for i in sg["issues"])
