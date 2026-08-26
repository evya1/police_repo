"""Agreement signs every material field in the complete official result."""

from __future__ import annotations

from copy import deepcopy

from common.transport import kit_consensus as consensus


def _result_scope(kit_result: dict, kit_game_id: str) -> tuple[dict, list[dict]]:
    return deepcopy(kit_result["final_result"]), deepcopy(kit_result["sub_games"])


def test_consensus_is_deterministic(kit_result, kit_game_id):
    final, rows = _result_scope(kit_result, kit_game_id)
    scope = consensus.consensus_scope(kit_game_id, final, rows)
    assert consensus.consensus_sha256(scope) == consensus.consensus_sha256(scope)


def test_every_official_row_field_is_signed(kit_result, kit_game_id):
    final, rows = _result_scope(kit_result, kit_game_id)
    original = consensus.consensus_sha256(consensus.consensus_scope(kit_game_id, final, rows))
    for key in rows[0]:
        changed = deepcopy(rows)
        changed[0][key] = {"changed": True}
        digest = consensus.consensus_sha256(
            consensus.consensus_scope(kit_game_id, final, changed)
        )
        assert digest != original, key


def test_every_aggregate_field_is_signed(kit_result, kit_game_id):
    final, rows = _result_scope(kit_result, kit_game_id)
    original = consensus.consensus_sha256(consensus.consensus_scope(kit_game_id, final, rows))
    for key in final:
        changed = deepcopy(final)
        changed[key] = {"changed": True}
        digest = consensus.consensus_sha256(
            consensus.consensus_scope(kit_game_id, changed, rows)
        )
        assert digest != original, key


def test_mutual_agreement_reports_confirmation_honestly(kit_result, kit_game_id):
    rows = kit_result["sub_games"]
    block = consensus.mutual_agreement(
        kit_game_id, kit_result["final_result"], rows, confirmed=False
    )
    assert len(block["sha256"]) == 64
    assert block["confirmed"] is False
