"""Each artifact must carry the keys the kit's checker REQUIRES, and refuse an unwrapped record."""

from __future__ import annotations

import hashlib

import pytest

from common.transport import kit_documents as docs
from common.transport.canonical import canonical_bytes
from common.transport.kit_records import KitDocumentError

#: Copied verbatim from the kit's tools/check_artifacts.py REQUIRED table.
KIT_REQUIRED = {
    "declaration": {"game_id", "game_uid", "groups", "num_sub_games"},
    "config": {"game_id", "game_uid", "sub_game_number"},
    "log": {"game_id", "game_uid", "summary", "records"},
    "result": {"game_id", "game_uid", "groups", "num_sub_games", "sub_games", "final_result"},
}

IDS = {"game_id": "a-vs-b", "game_uid": "3f2a6b1c-0000-4000-8000-000000000001"}
TERMS = {"board_size": 7, "max_steps": 35, "num_games": 6}
TIMES = {
    "timezone": "Asia/Jerusalem",
    "game_started_at": "2026-08-26T12:00:00+03:00",
    "game_ended_at": "2026-08-26T12:10:00+03:00",
}


def wrapped(step: int) -> dict:
    payload = {"step": step, "move": "STAY"}
    return {"payload": payload, "nonce": "n" * 32, "commit": "c" * 64}


def a_summary() -> dict:
    return docs.build_summary(
        sub_game_number=1, our_group="a", our_role="police", opponent_group="b",
        result="capture", winner_group="a", steps=6,
        audit={"passed": True, "skipped": False, "verified_steps": 7, "failed_steps": []},
    )


def test_declaration_carries_the_required_keys():
    doc = docs.build_declaration(
        **IDS, groups=[{"group_id": "a"}, {"group_id": "b"}], num_sub_games=6, **TIMES
    )
    assert KIT_REQUIRED["declaration"] <= set(doc)
    assert doc["groups"]["group_1"]["group_id"] == "a"
    assert doc["groups"]["group_2"]["group_id"] == "b"


def test_declaration_refuses_anything_but_two_groups():
    with pytest.raises(KitDocumentError, match="exactly two groups"):
        docs.build_declaration(**IDS, groups=[{"group_id": "a"}], num_sub_games=6, **TIMES)


def test_config_carries_required_keys_and_digests_its_own_terms():
    doc = docs.build_config(**IDS, sub_game_number=3, terms=TERMS)
    assert KIT_REQUIRED["config"] <= set(doc)
    assert doc["sub_game_number"] == 3
    assert all(doc[key] == value for key, value in TERMS.items())
    assert doc["config_sha256"] == hashlib.sha256(canonical_bytes(TERMS)).hexdigest()


def test_log_carries_required_keys_and_passes_records_through_untouched():
    records = [wrapped(0), wrapped(1)]
    doc = docs.build_log(**IDS, sub_game_number=1, summary=a_summary(), records=records)
    assert KIT_REQUIRED["log"] <= set(doc)
    assert doc["records"] == records, "the builder must never reshape a sealed record"


def test_log_refuses_a_flat_internal_record():
    """The exact defect that made every honest log read as tampered."""
    flat = {"step": 1, "move": "STAY", "nonce": "n" * 32, "commit": "c" * 64}
    with pytest.raises(KitDocumentError, match="already be wrapped"):
        docs.build_log(**IDS, sub_game_number=1, summary=a_summary(), records=[flat])


def test_log_refuses_a_non_object_payload():
    bad = {"payload": "not-an-object", "nonce": "n" * 32, "commit": "c" * 64}
    with pytest.raises(KitDocumentError, match="non-object payload"):
        docs.build_log(**IDS, sub_game_number=1, summary=a_summary(), records=[bad])


def test_log_omits_the_opponent_half_when_there_is_none():
    doc = docs.build_log(**IDS, sub_game_number=1, summary=a_summary(), records=[wrapped(1)])
    assert "opponent_records" not in doc


def test_result_carries_the_required_keys():
    rows = [{"sub_game_number": 1, "score": {"a": 20, "b": 5}}]
    doc = docs.build_result(
        **IDS, groups=["a", "b"], sub_games=rows, final_result={"total_score": {"a": 20, "b": 5}}
    )
    assert KIT_REQUIRED["result"] <= set(doc)
    assert doc["num_sub_games"] == 1


def test_the_league_posture_block_is_never_defaulted():
    """An armed counted/uncounted marker on a run nobody described is a false declaration."""
    for doc in (
        docs.build_declaration(
            **IDS, groups=[{"group_id": "a"}, {"group_id": "b"}], num_sub_games=6, **TIMES
        ),
        docs.build_config(**IDS, sub_game_number=1, terms=TERMS),
        docs.build_log(**IDS, sub_game_number=1, summary=a_summary(), records=[wrapped(1)]),
        docs.build_result(**IDS, groups=["a", "b"], sub_games=[], final_result={}),
    ):
        assert "league" not in doc
    armed = docs.build_config(**IDS, sub_game_number=1, terms=TERMS, league={"counted": True})
    assert armed["league"] == {"counted": True}


def test_unknown_optionals_are_omitted_rather_than_nulled():
    doc = docs.build_declaration(
        **IDS, groups=[{"group_id": "a"}, {"group_id": "b"}], num_sub_games=6, **TIMES
    )
    assert "max_tokens_per_game" not in doc
    assert "step_zero" not in doc


def test_every_document_declares_the_official_v11_schema():
    built = [
        docs.build_declaration(
            **IDS, groups=[{"group_id": "a"}, {"group_id": "b"}], num_sub_games=6, **TIMES
        ),
        docs.build_config(**IDS, sub_game_number=1, terms=TERMS),
        docs.build_log(**IDS, sub_game_number=1, summary=a_summary(), records=[wrapped(1)]),
        docs.build_result(**IDS, groups=["a", "b"], sub_games=[], final_result={}),
    ]
    for doc in built:
        assert doc["schema_version"] == "1.1"
        assert len(doc["_schema"]) > 200
        assert "schema_profile" not in doc


def test_log_uses_the_official_winner_role_and_agreement_identity():
    summary = a_summary()
    summary["winner_role"] = "police"
    summary.pop("winner_group")
    doc = docs.build_log(**IDS, sub_game_number=1, summary=summary, records=[wrapped(1)])
    assert doc["summary"]["winner_role"] == "police"
    assert doc["mutual_agreement"]["opponent_group_id"] == "b"


def test_shapes_match_the_pinned_kit_bundle(kit_declaration, kit_config, kit_log, kit_result):
    """Our required-key expectations are the kit's own, checked against its own bundle."""
    assert KIT_REQUIRED["declaration"] <= set(kit_declaration)
    assert KIT_REQUIRED["config"] <= set(kit_config)
    assert KIT_REQUIRED["log"] <= set(kit_log)
    assert KIT_REQUIRED["result"] <= set(kit_result)
