"""Integration: publish a replay bundle from a real settled series (T046, RP-07/RP-12)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from common.domain.scoring import Role
from common.transport.loopback import pair
from common.transport.replay import verify_replay
from common.transport.replay_types import ReplayVerdict
from common.transport.series import PeerConfig, SeriesResult, run_series
from police_peer.reporting.replay_bundle import publish_replay_bundle
from police_peer.runner import write_artifacts
from police_peer.wire import StandInEngine

_TERMS = {
    "board_size": 7, "smell_grid_size": 5, "decay_per_step": 0.1, "emit_intensity": 0.9,
    "min_center_intensity": 0.5, "max_steps": 35, "barriers_max": 14, "setting": "New York",
    "hint_max_words": 15, "axis_origin_corner": "top-left", "axis_start_index": 0,
    "thief_start": [3, 3], "cop_start": [0, 0], "num_games": 6,
}
_SUMMARY_KEYS = {
    "group_id", "mode", "natural_role", "game_id", "game_uid",
    "settled", "settled_outcome", "ledger",
}


class DummyBudgets:
    turn_timeout = 10.0
    connect_timeout = 10.0
    poll_interval = 0.005


def _run_settled_pair() -> tuple[SeriesResult, SeriesResult]:
    a, b = pair("A", "B")
    config_a = PeerConfig(natural_role=Role.POLICE, budgets=DummyBudgets(), terms=_TERMS)
    config_b = PeerConfig(natural_role=Role.THIEF, budgets=DummyBudgets(), terms=_TERMS)
    return run_series(
        a, b, config_a, config_b, StandInEngine(Role.POLICE), StandInEngine(Role.THIEF)
    )


class TestPublishFromRealSettledSeries:
    def test_bundle_has_exact_counts_digests_and_identity(self, tmp_path: Path) -> None:
        result_a, _ = _run_settled_pair()
        assert result_a.settled

        dest = publish_replay_bundle(tmp_path, result_a)
        assert dest == tmp_path / "replay" / result_a.game_uid
        assert len(list(dest.iterdir())) == 15

        manifest = json.loads((dest / f"manifest_{result_a.game_id}.json").read_text("utf-8"))
        assert manifest["game_uid"] == result_a.game_uid
        assert manifest["game_id"] == result_a.game_id
        assert manifest["schema_status"] == "internal_interop"
        assert len(manifest["members"]) == 14
        for member in manifest["members"]:
            digest = hashlib.sha256((dest / member["name"]).read_bytes()).hexdigest()
            assert digest == member["sha256"]

        for i in range(1, 7):
            cfg = json.loads((dest / f"config_{result_a.game_id}_g{i:02d}.json").read_text("utf-8"))
            log = json.loads((dest / f"log_{result_a.game_id}_g{i:02d}.json").read_text("utf-8"))
            assert cfg["sub_game_index"] == i == log["sub_game_index"]
            assert cfg["game_uid"] == result_a.game_uid == log["game_uid"]
            report = verify_replay(log, cfg)
            assert report.verdict not in (ReplayVerdict.INVALID, ReplayVerdict.INCOMPLETE)

    def test_existing_summary_artifact_output_is_unchanged(self, tmp_path: Path) -> None:
        result_a, _ = _run_settled_pair()
        write_artifacts(tmp_path, result_a, role=Role.POLICE, group_id="g", mode="warmup")
        summary_path = tmp_path / f"result_{result_a.game_id}.json"
        before = json.loads(summary_path.read_text("utf-8"))
        assert set(before.keys()) == _SUMMARY_KEYS
        assert len(before["ledger"]) == 6

        publish_replay_bundle(tmp_path, result_a)

        after = json.loads(summary_path.read_text("utf-8"))
        assert after == before  # publishing the replay bundle must not touch the summary
