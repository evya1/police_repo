import pytest

from police_peer.reporting.schemas import (
    FinalizedLogMutationError,
    SchemaError,
    assert_lifecycle_ok,
    build_declaration,
    build_series_result,
    build_sub_game_config,
    build_sub_game_log,
)


def test_artifact_lifecycle():
    # Test valid lifecycle stages
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
    assert_lifecycle_ok(declaration, "pre_series")

    config = build_sub_game_config(
        game_uid="test_game",
        game_id="test_game:0",
        sub_game_index=0,
        role_for_this_sub_game="police",
        agreed_terms={},
        git_commit="abc123",
    )
    assert_lifecycle_ok(config, "pre_sub_game")

    log = build_sub_game_log(game_uid="test_game", game_id="test_game:0")
    assert_lifecycle_ok(log, "during_sub_game")

    result = build_series_result(
        game_uid="test_game",
        sub_game_results=[],
        total_police_score=0,
        total_thief_score=0,
        tie_applied=False,
        repo_links={},
        total_llm_tokens_per_series=0,
    )
    assert_lifecycle_ok(result, "post_settlement")

    # Test invalid lifecycle stages
    with pytest.raises(SchemaError):
        assert_lifecycle_ok(declaration, "post_settlement")

    with pytest.raises(SchemaError):
        assert_lifecycle_ok(result, "pre_series")

    # Test finalize_log
    log = build_sub_game_log(game_uid="test_game", game_id="test_game:0")
    assert not log.finalized
    assert log.signature is None

    # Mock signer
    def mock_signer(data):
        return "mock_signature"

    log = log.__class__(**log.as_dict())
    log = log.__class__(**log.as_dict())
    finalized_log = log  # Placeholder for actual finalize_log call
    # This would require a real finalize_log implementation to test fully
    # But we can at least check that it sets finalized=True and signature
    # For now, just ensure it doesn't raise an error on valid inputs

    # Test mutation of finalized log
    finalized_log.finalized = True
    with pytest.raises(FinalizedLogMutationError):
        finalized_log.steps = [{"state": "test"}]
