"""Differential contracts against Yoram Segal's four complete sample documents."""

from __future__ import annotations

import hashlib

import pytest

from common.transport import kit_documents as docs
from common.transport.canonical import canonical_bytes
from common.transport.kit_records import KitDocumentError

_CONFIG_ENVELOPE = {
    "_schema", "game_id", "game_uid", "sub_game_number", "links", "config_name",
    "config_sha256",
}


def test_declaration_builder_reproduces_yorams_complete_sample(yoram_declaration) -> None:
    reference = yoram_declaration
    built = docs.build_declaration(
        game_id=reference["game_id"], game_uid=reference["game_uid"],
        groups=list(reference["groups"].values()), num_sub_games=reference["num_sub_games"],
        timezone=reference["timezone"], game_started_at=reference["game_started_at"],
        game_ended_at=reference["game_ended_at"],
        max_tokens_per_game=reference["max_tokens_per_game"],
    )
    assert built == reference


def test_config_builder_reproduces_yorams_hash_scope_and_complete_sample(yoram_config) -> None:
    reference = yoram_config
    shared = {key: value for key, value in reference.items() if key not in _CONFIG_ENVELOPE}
    built = docs.build_config(
        game_id=reference["game_id"], game_uid=reference["game_uid"],
        sub_game_number=reference["sub_game_number"], terms=shared,
    )
    assert built == reference
    assert built["config_sha256"] == hashlib.sha256(canonical_bytes(shared)).hexdigest()


def test_log_builder_reproduces_yorams_complete_sample(yoram_log) -> None:
    reference = yoram_log
    built = docs.build_log(
        game_id=reference["game_id"], game_uid=reference["game_uid"],
        summary=reference["summary"], records=reference["records"],
    )
    assert built == reference


def test_result_builder_reproduces_yorams_complete_sample(yoram_result) -> None:
    reference = yoram_result
    built = docs.build_result(
        game_id=reference["game_id"], game_uid=reference["game_uid"],
        groups=reference["groups"], sub_games=reference["sub_games"],
        final_result=reference["final_result"], mutual_agreement=reference["mutual_agreement"],
    )
    assert built == reference


def test_config_projection_whitelists_only_reference_fields(yoram_config) -> None:
    reference = yoram_config
    shared = {key: value for key, value in reference.items() if key not in _CONFIG_ENVELOPE}
    shared["world"] = {"map_area": "New York"}
    shared["scoring"] = {**shared["scoring"], "technical_loss": 0}
    shared["network_and_league"] = {
        **shared["network_and_league"], "diversity_reward": 10,
    }

    built = docs.build_config(
        game_id=reference["game_id"], game_uid=reference["game_uid"],
        sub_game_number=1, terms=shared,
    )

    assert "world" not in built
    assert "technical_loss" not in built["scoring"]
    assert "diversity_reward" not in built["network_and_league"]


def test_declaration_whitelists_group_fields_and_recomputes_signature(yoram_declaration) -> None:
    reference = yoram_declaration
    groups = [
        {**group, "github_commit": "a" * 40, "counted_games_played": 9}
        for group in reference["groups"].values()
    ]
    built = docs.build_declaration(
        game_id=reference["game_id"], game_uid=reference["game_uid"], groups=groups,
        num_sub_games=6, timezone=reference["timezone"],
        game_started_at=reference["game_started_at"], game_ended_at=reference["game_ended_at"],
        max_tokens_per_game=reference["max_tokens_per_game"],
    )
    assert all("github_commit" not in group for group in built["groups"].values())
    assert all("counted_games_played" not in group for group in built["groups"].values())


def test_declaration_refuses_anything_but_two_groups(yoram_declaration) -> None:
    reference = yoram_declaration
    with pytest.raises(KitDocumentError, match="exactly two groups"):
        docs.build_declaration(
            game_id=reference["game_id"], game_uid=reference["game_uid"], groups=[],
            num_sub_games=6, timezone=reference["timezone"],
            game_started_at=reference["game_started_at"],
            game_ended_at=reference["game_ended_at"],
            max_tokens_per_game=reference["max_tokens_per_game"],
        )


def test_log_refuses_a_flat_internal_record(yoram_log) -> None:
    flat = {"step": 1, "move": "STAY", "nonce": "n" * 32, "commit": "c" * 64}
    with pytest.raises(KitDocumentError, match="already be wrapped"):
        docs.build_log(
            game_id=yoram_log["game_id"], game_uid=yoram_log["game_uid"],
            summary=yoram_log["summary"], records=[flat],
        )


def test_all_official_roots_have_no_custom_fields(
    yoram_declaration, yoram_config, yoram_log, yoram_result,
) -> None:
    forbidden = {"schema_profile", "league", "step_zero", "opponent_records",
                 "opponent_committed_steps", "terms"}
    for reference in (yoram_declaration, yoram_config, yoram_log, yoram_result):
        assert not forbidden & set(reference)
