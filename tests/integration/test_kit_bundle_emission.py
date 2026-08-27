"""The emitted kit bundle must satisfy the kit's own gates without the kit installed."""

from __future__ import annotations

import json
import shutil
import threading
from pathlib import Path

import pytest

from common.config import load_config
from common.domain.scoring import Role
from common.transport.canonical import commit as recompute
from common.transport.kit_bundle_validation import validate_official_bundle
from common.transport.kit_identity import GroupIdentity, group_block
from common.transport.kit_settlement import TIE_SCORE
from common.transport.loopback import pair
from common.transport.series import PeerFacade, SeriesResult
from police_peer.reporting.kit_bundle import publish_kit_bundle
from police_peer.sdk import Budgets, create_peer

POLICE, THIEF = "kit-police", "kit-thief"
HARDWARE = {
    "cpu_type": "Example CPU", "cpu_freq_mhz": 2400.0, "cpu_cores": 2,
    "ram_gb": 4.0, "gpu_model": None, "vram_gb": None,
}


def _identity(group: str, commit: str) -> dict:
    return group_block(GroupIdentity(
        group_id=group, group_name=group, members=(f"{group}-member",),
        repos={"cop": "https://example.invalid/cop", "thief": "https://example.invalid/thief"},
        mcp_servers={"cop": "http://127.0.0.1:8101/mcp", "thief": "http://127.0.0.1:8102/mcp"},
        llm_model="template", hardware_spec=HARDWARE,
        github_commit=commit, counted_games_played=0, code_version="1.0.0",
    ))


@pytest.fixture(scope="module")
def official_args() -> dict:
    config = load_config(Path(__file__).resolve().parents[2] / "config" / "game.json")
    config["agreed_between"] = [POLICE, THIEF]
    return {
        "groups": [_identity(POLICE, "a" * 40), _identity(THIEF, "b" * 40)],
        "agreed_config": config,
        "confirmed": True,
        "max_tokens_per_game": 200_000,
        "tokens_by_sub_game": {
            number: {POLICE: 0, THIEF: 0} for number in range(1, 7)
        },
    }


@pytest.fixture(scope="module")
def series() -> SeriesResult:
    config = Path(__file__).resolve().parents[2] / "config" / "game.json"
    channel_a, channel_b = pair(POLICE, THIEF)
    budgets = Budgets(turn_timeout=10.0, connect_timeout=10.0, poll_interval=0.005)
    police = create_peer(config, channel=channel_a, role=Role.POLICE, group_id=POLICE,
                         budgets=budgets)
    thief = create_peer(config, channel=channel_b, role=Role.THIEF, group_id=THIEF,
                        budgets=budgets)
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
    return out["p"]


@pytest.fixture(scope="module")
def bundle(series, official_args, tmp_path_factory) -> Path:
    root = tmp_path_factory.mktemp("kit")
    return publish_kit_bundle(
        root, series, our_group=POLICE, counted=False, **official_args
    )


def docs(bundle: Path) -> dict[str, dict]:
    return {p.name: json.loads(p.read_text(encoding="utf-8")) for p in bundle.glob("*.json")}


def test_the_bundle_is_exactly_fourteen_flat_files(bundle):
    files = sorted(p.name for p in bundle.iterdir())
    assert len(files) == 14, files
    assert not [p for p in bundle.iterdir() if p.is_dir()], "the kit reads ONE flat directory"


def test_validator_rejects_missing_and_mismatched_artifacts(bundle, tmp_path):
    missing = tmp_path / "missing"
    shutil.copytree(bundle, missing)
    next(missing.glob("config_*_g03.json")).unlink()
    with pytest.raises(Exception, match="file set mismatch"):
        validate_official_bundle(missing)

    mismatched = tmp_path / "mismatched"
    shutil.copytree(bundle, mismatched)
    path = next(mismatched.glob("log_*_g04.json"))
    document = json.loads(path.read_text())
    document["game_uid"] = "different"
    path.write_text(json.dumps(document))
    with pytest.raises(Exception, match="identifiers mismatch"):
        validate_official_bundle(mismatched)


def test_every_sealed_record_reproduces_its_commitment(bundle):
    checked = 0
    for name, doc in docs(bundle).items():
        if not name.startswith("log_"):
            continue
        assert "opponent_records" not in doc
        for record in doc["records"]:
            assert set(record) == {"payload", "nonce", "commit"}
            assert recompute(record["payload"], record["nonce"]) == record["commit"]
            checked += 1
    assert checked > 0


def test_totals_are_the_sum_of_the_rows(bundle):
    result = next(d for n, d in docs(bundle).items() if n.startswith("result_"))
    final = result["final_result"]
    summed = {
        g: sum(row["score"][g] for row in result["sub_games"]) for g in result["groups"]
    }
    addend = TIE_SCORE if final["series_tie"] else 0
    assert final["total_score"] == {g: v + addend for g, v in summed.items()}
    assert set(final) == {
        "total_score", "sub_games_won", "ties", "winner_group", "series_tie",
        "tokens_total_series",
    }


def test_unknown_or_omitted_token_evidence_fails_closed(series, official_args, tmp_path):
    args = {**official_args, "tokens_by_sub_game": None}
    with pytest.raises(Exception, match="token evidence"):
        publish_kit_bundle(tmp_path, series, our_group=POLICE, counted=False, **args)
    with pytest.raises(Exception, match="token evidence"):
        publish_kit_bundle(
            tmp_path, series, our_group=POLICE, counted=False,
            include_tokens=False, **official_args,
        )


def test_declaration_and_result_agree_on_the_series_length(bundle):
    every = docs(bundle)
    declaration = next(d for n, d in every.items() if n.startswith("declaration_"))
    result = next(d for n, d in every.items() if n.startswith("result_"))
    assert declaration["num_sub_games"] == result["num_sub_games"] == 6
    assert all(len(group["signature"]) == 64 for group in declaration["groups"].values())
    assert all(
        set(group["hardware_spec"]) == set(HARDWARE)
        for group in declaration["groups"].values()
    )


def test_every_logged_sub_game_appears_in_the_result(bundle):
    every = docs(bundle)
    logged = {d["summary"]["sub_game_number"] for n, d in every.items() if n.startswith("log_")}
    listed = {row["sub_game_number"] for n, d in every.items()
              if n.startswith("result_") for row in d["sub_games"]}
    assert logged <= listed
    assert logged == set(range(1, 7))
