"""The emitted kit bundle must satisfy the kit's own gates without the kit installed."""

from __future__ import annotations

import hashlib
import json
import re
import threading
import uuid
from pathlib import Path

import pytest

from common.domain.scoring import Role
from common.transport.canonical import canonical_bytes
from common.transport.canonical import commit as recompute
from common.transport.ids import game_uid as derive_uid
from common.transport.loopback import pair
from common.transport.series import PeerFacade, SeriesResult
from common.transport.terms import TERMS_KEYS
from police_peer.evidence.token_ledger import TokenLedger
from police_peer.evidence.tokens import TokenEvent, UsageStatus
from police_peer.reporting.kit_bundle import publish_kit_bundle
from police_peer.reporting.settlement import publish_kit
from police_peer.sdk import Budgets, create_peer

KIT_NAME_RE = re.compile(r"^(declaration|config|log|result)_(?P<gid>.+?)(?:_g(?P<nn>\d+))?\.json$")
POLICE, THIEF = "kit-police", "kit-thief"


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
def bundle(series, tmp_path_factory) -> Path:
    root = tmp_path_factory.mktemp("kit")
    return publish_kit_bundle(root, series, our_group=POLICE, counted=False)


def docs(bundle: Path) -> dict[str, dict]:
    return {p.name: json.loads(p.read_text(encoding="utf-8")) for p in bundle.glob("*.json")}


def test_the_bundle_is_exactly_fourteen_flat_files(bundle):
    files = sorted(p.name for p in bundle.iterdir())
    assert len(files) == 14, files
    assert not [p for p in bundle.iterdir() if p.is_dir()], "the kit reads ONE flat directory"


def test_every_filename_parses_under_the_kits_own_grammar(bundle):
    for name in sorted(p.name for p in bundle.iterdir()):
        assert KIT_NAME_RE.match(name), name


def test_one_game_uid_joins_every_artifact(bundle):
    uids = {d["game_uid"] for d in docs(bundle).values()}
    assert len(uids) == 1
    uuid.UUID(uids.pop())


def test_the_uid_re_derives_from_the_flat_fourteen_key_terms(bundle, series):
    """The failure a consistency check cannot see: a uid built from a wider object."""
    every = docs(bundle)
    terms = next(d["terms"] for n, d in every.items() if n.startswith("config_"))
    assert set(terms) == set(TERMS_KEYS), "the config must carry exactly the flat signed terms"
    assert derive_uid(terms, POLICE, THIEF) == series.game_uid


def test_the_game_id_is_the_sorted_pair_not_self_first(series):
    assert series.game_id == "-vs-".join(sorted([POLICE, THIEF]))


def test_every_sealed_record_reproduces_its_commitment(bundle):
    checked = 0
    for name, doc in docs(bundle).items():
        if not name.startswith("log_"):
            continue
        for half in ("records", "opponent_records"):
            for record in doc.get(half) or []:
                assert set(record) == {"payload", "nonce", "commit"}
                assert recompute(record["payload"], record["nonce"]) == record["commit"]
                checked += 1
    assert checked > 0


def test_the_config_digest_matches_its_own_terms(bundle):
    for name, doc in docs(bundle).items():
        if name.startswith("config_"):
            expected = hashlib.sha256(canonical_bytes(doc["terms"])).hexdigest()
            assert doc["config_sha256"] == expected


def test_totals_are_the_sum_of_the_rows(bundle):
    result = next(d for n, d in docs(bundle).items() if n.startswith("result_"))
    final = result["final_result"]
    summed = {
        g: sum(row["score"][g] for row in result["sub_games"]) for g in result["groups"]
    }
    addend = final.get("tie_score_each", 0) if final["series_tie"] else 0
    assert final["total_score"] == {g: v + addend for g, v in summed.items()}


def test_tokens_total_is_the_sum_of_the_per_row_tokens(bundle):
    result = next(d for n, d in docs(bundle).items() if n.startswith("result_"))
    derived = {
        g: sum(row["tokens"].get(g, 0) for row in result["sub_games"])
        for g in result["groups"]
    }
    assert result["final_result"]["tokens_total_series"] == derived


def test_runtime_token_ledger_reaches_kit_rows_and_total(series, tmp_path):
    ledger = TokenLedger()
    event = TokenEvent(sub_game_id="1", step=1, counted=False, provider_called=True,
                       fallback=False, status=UsageStatus.KNOWN_NONZERO, input_tokens=17, output_tokens=4)
    ledger.record(event)
    publish_kit(tmp_path, series, our_group=POLICE, mode="warmup", confirmed=False,
                token_ledger=ledger)
    emitted = docs(tmp_path / "kit" / series.game_uid)
    result = next(doc for name, doc in emitted.items() if name.startswith("result_"))
    assert result["sub_games"][0]["tokens"][POLICE] == 21
    assert result["final_result"]["tokens_total_series"][POLICE] == 21


def test_a_warm_up_never_arms_the_league_fields(bundle):
    result = next(d for n, d in docs(bundle).items() if n.startswith("result_"))
    assert set(result["final_result"]["diversity_reward_applied"].values()) == {False}
    assert "league" not in result


def test_declaration_and_result_agree_on_the_series_length(bundle):
    every = docs(bundle)
    declaration = next(d for n, d in every.items() if n.startswith("declaration_"))
    result = next(d for n, d in every.items() if n.startswith("result_"))
    assert declaration["num_sub_games"] == result["num_sub_games"] == 6


def test_step_zero_reaches_the_declaration(series, tmp_path):
    step_zero = {"group_id": POLICE, "github_commit": "a" * 40, "signature": "sealed"}
    emitted = publish_kit_bundle(
        tmp_path, series, our_group=POLICE, counted=False, step_zero=step_zero,
    )
    declaration = next(
        document for name, document in docs(emitted).items()
        if name.startswith("declaration_")
    )
    assert declaration["step_zero"] == step_zero


def test_every_logged_sub_game_appears_in_the_result(bundle):
    every = docs(bundle)
    logged = {d["sub_game_number"] for n, d in every.items() if n.startswith("log_")}
    listed = {row["sub_game_number"] for n, d in every.items()
              if n.startswith("result_") for row in d["sub_games"]}
    assert logged <= listed
    assert logged == set(range(1, 7))


def test_the_internal_bundle_is_untouched_by_the_projection(series, tmp_path):
    """The kit bundle is written beside the evidence of record, never over it."""
    from police_peer.reporting.replay_bundle import publish_replay_bundle
    from police_peer.sdk import verify_replay_bundle

    internal = publish_replay_bundle(tmp_path, series)
    publish_kit_bundle(tmp_path, series, our_group=POLICE, counted=False)
    assert len(list(internal.iterdir())) == 15
    assert verify_replay_bundle(internal).verdict.value == "verified_ok"
