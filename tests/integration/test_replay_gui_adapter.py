import json
from pathlib import Path

import pytest

from police_peer.replay_gui import ReplayGuiError, resolve_log, verify_replay_log

FIXTURE = Path("tests/fixtures/kit_reference/log_team-aleph-vs-team-bet_g01.json")


def test_viewer_verifies_repository_kit_fixture() -> None:
    ok, report = verify_replay_log(FIXTURE)
    assert ok
    assert "Verified OK" in report
    assert "both halves" in report


def test_viewer_refuses_a_tampered_opponent_record(tmp_path: Path) -> None:
    document = json.loads(FIXTURE.read_text(encoding="utf-8"))
    document["opponent_records"][0]["payload"]["position"] = [6, 6]
    tampered = tmp_path / FIXTURE.name
    tampered.write_text(json.dumps(document), encoding="utf-8")
    ok, report = verify_replay_log(tampered)
    assert not ok
    assert "TAMPERED" in report


def test_bundle_directory_selects_first_log_and_empty_directory_fails(tmp_path: Path) -> None:
    assert resolve_log(FIXTURE.parent).name.endswith("g01.json")
    with pytest.raises(ReplayGuiError):
        resolve_log(tmp_path)
