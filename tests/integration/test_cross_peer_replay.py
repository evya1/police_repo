"""Cross-peer replay: this repository's own CLI/service consumes a frozen bundle it did not
generate in this test run (T047, RP-11). No import of ``thief_peer`` anywhere in this file;
when the sibling checkout is present, its own CLI is exercised as a real subprocess.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from police_peer.sdk import verify_replay_bundle

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SIBLING_ROOT = _REPO_ROOT.parent / "thief_repo"
_CLI = _REPO_ROOT / "scripts" / "replay.py"
_FIXTURE_DIR = _REPO_ROOT / "tests" / "fixtures" / "replay" / "sibling_v1"
_FIXTURE_UID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"


def _fixture() -> Path:
    return _FIXTURE_DIR / _FIXTURE_UID


def test_frozen_sibling_fixture_verifies_through_our_own_service() -> None:
    report = verify_replay_bundle(_fixture())
    assert report.verdict.value == "verified_ok"
    assert report.coverage.bundle_digests is True
    assert report.coverage.external_authenticity is False
    assert len(report.sub_games) == 6


def test_frozen_sibling_fixture_verifies_through_our_own_cli() -> None:
    proc = subprocess.run(
        [sys.executable, str(_CLI), str(_fixture()), "--json"],
        cwd=_REPO_ROOT, capture_output=True, text=True, check=False,
    )
    assert proc.returncode == 0
    assert json.loads(proc.stdout)["verdict"] == "verified_ok"


def test_recorded_provenance_matches_the_checked_in_bytes() -> None:
    """Every member's SHA-256 in the manifest still matches the file on disk — a rot/
    accidental-edit check on the fixture itself, independent of the service under test.
    """
    d = _fixture()
    manifest = json.loads((d / "manifest_A-vs-B.json").read_text("utf-8"))
    assert len(manifest["members"]) == 14
    for member in manifest["members"]:
        digest = hashlib.sha256((d / member["name"]).read_bytes()).hexdigest()
        assert digest == member["sha256"], f"provenance drift: {member['name']}"


def test_sibling_repository_never_imported() -> None:
    import sys as _sys

    assert not any(name == "thief_peer" or name.startswith("thief_peer.") for name in _sys.modules)


@pytest.mark.skipif(
    not (_SIBLING_ROOT / "scripts" / "replay.py").is_file(),
    reason="sibling checkout has no replay CLI yet (its own T047 is not complete)",
)
def test_live_sibling_cli_verifies_a_bundle_we_publish() -> None:
    """When the sibling checkout has its own CLI, it verifies our fixture as a subprocess
    run in *its own* working directory — never imported, never added to sys.path.
    """
    proc = subprocess.run(
        ["uv", "run", "python", "scripts/replay.py", str(_fixture()), "--json"],
        cwd=_SIBLING_ROOT, capture_output=True, text=True, check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout)["verdict"] == "verified_ok"
