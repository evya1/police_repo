"""A loopback counted-shaped run produces a declaration that verifies end to end (T057)."""

from __future__ import annotations

import threading
from pathlib import Path

import pytest

from common.domain.scoring import Role
from common.transport.kit_identity import GroupIdentity, group_block, verify_group_block
from common.transport.loopback import pair
from common.transport.series import PeerFacade, SeriesResult
from police_peer.reporting.kit_bundle import publish_kit_bundle
from police_peer.sdk import Budgets, create_peer

POLICE, THIEF = "decl-police", "decl-thief"
COMMIT_A = "1" * 40
COMMIT_B = "2" * 40


def _identity(group: str, commit: str, counted_games_played: int) -> GroupIdentity:
    counted = counted_games_played
    return GroupIdentity(
        group_id=group,
        group_name=group,
        members=("Member One", "Member Two"),
        repos={"cop": f"https://github.com/{group}/cop", "thief": f"https://github.com/{group}/thief"},
        mcp_servers={"cop": f"https://cop.{group}.example/mcp", "thief": f"https://thief.{group}.example/mcp"},
        llm_model="template",
        hardware_spec={"os": "Linux", "cpu_cores": 8},
        github_commit=commit,
        counted_games_played=counted,
        code_version="1.00",
    )


@pytest.fixture(scope="module")
def series() -> SeriesResult:
    config = Path(__file__).resolve().parents[2] / "config" / "game.json"
    channel_a, channel_b = pair(POLICE, THIEF)
    budgets = Budgets(turn_timeout=10.0, connect_timeout=10.0, poll_interval=0.005)
    police = create_peer(config, channel=channel_a, role=Role.POLICE, group_id=POLICE, budgets=budgets)
    thief = create_peer(config, channel=channel_b, role=Role.THIEF, group_id=THIEF, budgets=budgets)
    out: dict[str, SeriesResult] = {}
    errors: list[Exception] = []

    def go(name: str, facade: PeerFacade) -> None:
        try:
            out[name] = facade.run()
        except Exception as exc:  # noqa: BLE001 - surfaced below
            errors.append(exc)

    threads = [threading.Thread(target=go, args=("p", police)), threading.Thread(target=go, args=("t", thief))]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    if errors:
        raise errors[0]
    assert out["p"].settled
    return out["p"]


def test_declaration_verifies_and_counts_agree(series: SeriesResult, tmp_path_factory) -> None:
    our_identity = _identity(POLICE, COMMIT_A, counted_games_played=2)
    their_identity = _identity(THIEF, COMMIT_B, counted_games_played=4)
    ours_block = group_block(our_identity)
    theirs_block = group_block(their_identity)
    groups = sorted([ours_block, theirs_block], key=lambda b: b["group_id"])

    games_played = {
        POLICE: our_identity.counted_games_played + 1,
        THIEF: their_identity.counted_games_played + 1,
    }

    root = tmp_path_factory.mktemp("decl")
    bundle = publish_kit_bundle(
        root, series, our_group=POLICE, counted=True, groups=groups, games_played=games_played,
    )

    import json

    declaration = next(
        json.loads(p.read_text(encoding="utf-8"))
        for p in bundle.glob("declaration_*.json")
    )
    result = next(
        json.loads(p.read_text(encoding="utf-8")) for p in bundle.glob("result_*.json")
    )

    for group_block_doc in declaration["groups"].values():
        assert verify_group_block(group_block_doc)

    inclusive = result["final_result"]["games_played_including_this"]
    assert inclusive[POLICE] == our_identity.counted_games_played + 1
    assert inclusive[THIEF] == their_identity.counted_games_played + 1

    derived_tokens = {
        g: sum(row["tokens"].get(g, 0) for row in result["sub_games"]) for g in result["groups"]
    }
    assert result["final_result"]["tokens_total_series"] == derived_tokens


def test_an_unlearned_opponent_count_is_null_never_zero(series: SeriesResult, tmp_path_factory) -> None:
    our_identity = _identity(POLICE, COMMIT_A, counted_games_played=1)
    ours_block = group_block(our_identity)
    theirs_block = {"group_id": THIEF}  # nothing learned from their greeting (DEC-12)
    groups = sorted([ours_block, theirs_block], key=lambda b: b["group_id"])
    games_played = {POLICE: our_identity.counted_games_played + 1, THIEF: None}

    root = tmp_path_factory.mktemp("decl2")
    bundle = publish_kit_bundle(
        root, series, our_group=POLICE, counted=True, groups=groups, games_played=games_played,
    )

    import json

    result = next(
        json.loads(p.read_text(encoding="utf-8")) for p in bundle.glob("result_*.json")
    )
    assert result["final_result"]["games_played_including_this"][THIEF] is None
