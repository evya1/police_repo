"""A counted-shaped run produces a declaration whose evidence actually verifies."""

from __future__ import annotations

import hashlib
import threading
from pathlib import Path

import pytest

from common.config import load_config
from common.domain.scoring import Role
from common.transport.canonical import canonical_bytes
from common.transport.kit_identity import (
    GroupIdentity,
    identity_greeting_block,
    verify_group_block,
)
from common.transport.loopback import pair
from common.transport.series import PeerFacade, SeriesResult
from police_peer.evidence.identity_source import build_identity
from police_peer.league.preflight import FilePairingHistoryStore
from police_peer.reporting.kit_bundle import publish_kit_bundle
from police_peer.sdk import Budgets, create_peer
from police_peer.wire.config import PrivateConfig
from police_peer.wire.identity_config import Endpoints, GameIdentity

GROUP_A, GROUP_B = "decl-a", "decl-b"


def greeting_identity(group_id: str) -> dict:
    return identity_greeting_block(GroupIdentity(
        group_id=group_id, group_name=group_id, members=("id-1",),
        repos={"cop": "https://example.invalid/p", "thief": "https://example.invalid/t"},
        mcp_servers={"cop": "https://example.invalid/mcp", "thief": "https://example.invalid/mcp"},
        llm_model="template", hardware_spec={"cpu": "test"},
        github_commit="a" * 40, counted_games_played=0, code_version="1.0.0",
    ))


def an_identity(group_id: str, code_version: str, history: FilePairingHistoryStore) -> object:
    private = PrivateConfig(
        identity=GameIdentity(
            group_name=group_id, group_id=group_id, members=("id-1", "id-2"),
            repos={"cop": "https://example.invalid/p", "thief": "https://example.invalid/t"},
        ),
        endpoints=Endpoints(public_url="https://tunnel.invalid/mcp"),
    )
    return build_identity(
        private, group_id=group_id, repo_root=".", code_version=code_version, history=history,
    )


@pytest.fixture(scope="module")
def series() -> SeriesResult:
    config = Path(__file__).resolve().parents[2] / "config" / "game.json"
    channel_a, channel_b = pair(GROUP_A, GROUP_B)
    budgets = Budgets(turn_timeout=10.0, connect_timeout=10.0, poll_interval=0.005)
    police = create_peer(config, channel=channel_a, role=Role.POLICE, group_id=GROUP_A,
                         budgets=budgets, identity_block=greeting_identity(GROUP_A))
    thief = create_peer(config, channel=channel_b, role=Role.THIEF, group_id=GROUP_B,
                        budgets=budgets, identity_block=greeting_identity(GROUP_B))
    out: dict[str, SeriesResult] = {}
    errors: list[Exception] = []

    def go(name: str, facade: PeerFacade) -> None:
        try:
            out[name] = facade.run()
        except Exception as exc:  # noqa: BLE001 - surfaced below
            errors.append(exc)

    threads = [threading.Thread(target=go, args=("p", police)),
               threading.Thread(target=go, args=("t", thief))]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    if errors:
        raise errors[0]
    assert out["p"].settled
    assert out["p"].opponent_identity["group_id"] == GROUP_B
    assert "hardware_spec" in out["p"].opponent_identity
    return out["p"]


@pytest.fixture
def official_args(tmp_path) -> dict:
    history = FilePairingHistoryStore(tmp_path / "identity-history.json")
    from common.transport.kit_identity import group_block

    config = load_config(Path(__file__).resolve().parents[2] / "config" / "game.json")
    config["agreed_between"] = [GROUP_A, GROUP_B]
    return {
        "groups": [
            group_block(an_identity(GROUP_A, "1.0.0", history)),
            group_block(an_identity(GROUP_B, "1.0.0", history)),
        ],
        "agreed_config": config,
        "max_tokens_per_game": 200_000,
        "tokens_by_sub_game": {
            number: {GROUP_A: 0, GROUP_B: 0} for number in range(1, 7)
        },
        "confirmed": True,
    }


def test_declaration_carries_a_group_block_that_verifies(series, official_args, tmp_path):
    bundle = publish_kit_bundle(
        tmp_path / "bundle", series, our_group=GROUP_A, counted=True, **official_args,
    )
    import json

    declaration = json.loads(
        next(bundle.glob("declaration_*.json")).read_text(encoding="utf-8")
    )
    written = list(declaration["groups"].values())
    assert all(verify_group_block(g) for g in written)


def test_counted_games_played_and_the_inclusive_count_are_off_by_one(series, tmp_path):
    from common.transport.kit_settlement import series_final

    history = FilePairingHistoryStore(tmp_path / "history2.json")
    ours = an_identity(GROUP_A, "1.0.0", history)
    assert ours.counted_games_played == 0

    rows = [{
        "sub_game_number": 1, "score": {GROUP_A: 20, GROUP_B: 5}, "winner_group": GROUP_A,
        "tokens": {GROUP_A: 0, GROUP_B: 0},
    }]
    final = series_final(
        rows, (GROUP_A, GROUP_B), counted=True,
        games_played={GROUP_A: ours.counted_games_played + 1, GROUP_B: None},
    )
    assert final["games_played_including_this"][GROUP_A] == 1
    assert final["games_played_including_this"][GROUP_B] is None, "an unclaimed count is null"


def test_the_config_digest_in_the_bundle_matches_the_config(series, official_args, tmp_path):
    import json

    bundle = publish_kit_bundle(
        tmp_path / "bundle2", series, our_group=GROUP_A, counted=False, **official_args
    )
    config = json.loads(next(bundle.glob("config_*.json")).read_text(encoding="utf-8"))
    overlay = {
        "_schema", "game_id", "game_uid", "sub_game_number", "links", "config_name",
        "config_sha256",
    }
    shared = {key: value for key, value in config.items() if key not in overlay}
    assert config["config_sha256"] == hashlib.sha256(canonical_bytes(shared)).hexdigest()
