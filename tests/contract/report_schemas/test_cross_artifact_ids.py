import pytest

from police_peer.reporting.schemas import (
    IdentifierMismatchError,
    build_declaration,
    build_series_result,
    build_sub_game_config,
    build_sub_game_log,
    validate_identifiers,
)


def test_cross_artifact_ids():
    # Valid set
    declaration = build_declaration(
        game_uid="test_game",
        team="test_team",
        role="police",
        members=[],
        police_repo_url="http://example.com",
        thief_repo_url="http://example.com",
        mcp_addresses=[],
        hardware="test_hardware",
        model="test_model",
        token_budget=100,
        start_time="2023-01-01T00:00:00Z",
        end_time="2023-01-02T00:00:00Z",
    )

    config = build_sub_game_config(
        game_uid="test_game",
        game_id="test_game:0",
        sub_game_index=0,
        role_for_this_sub_game="police",
        agreed_terms={},
        git_commit="abc123",
    )

    log = build_sub_game_log(game_uid="test_game", game_id="test_game:0")

    result = build_series_result(
        game_uid="test_game",
        sub_game_results=[],
        total_police_score=0,
        total_thief_score=0,
        tie_applied=False,
        repo_links={},
        total_llm_tokens_per_series=0,
    )

    validate_identifiers(declaration, config, log, result)

    # Test mismatched game_uid
    config2 = build_sub_game_config(
        game_uid="different_game",
        game_id="different_game:0",
        sub_game_index=0,
        role_for_this_sub_game="police",
        agreed_terms={},
        git_commit="abc123",
    )
    with pytest.raises(IdentifierMismatchError):
        validate_identifiers(declaration, config2)

    # Test mismatched game_id in log
    log2 = build_sub_game_log(game_uid="test_game", game_id="different_game:0")
    with pytest.raises(IdentifierMismatchError):
        validate_identifiers(declaration, config, log2)
