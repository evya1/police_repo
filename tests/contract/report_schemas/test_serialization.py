import json

from police_peer.reporting.schemas import (
    build_declaration,
    build_series_result,
    build_sub_game_config,
    build_sub_game_log,
    canonical_bytes,
    serialize,
)


def test_serialization():
    # Test Declaration
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
    serialized = serialize(declaration)
    assert serialized == canonical_bytes(declaration.as_dict())

    # Test deterministic serialization
    serialized2 = serialize(declaration)
    assert serialized == serialized2

    # Test round-trip
    parsed = json.loads(serialized.decode("utf-8"))
    assert parsed == declaration.as_dict()

    # Test non-ASCII team name using a separate instance to avoid mutating shared state
    declaration_unicode = build_declaration(
        game_uid="test_game",
        team="测试团队",
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
    serialized_unicode = serialize(declaration_unicode)
    assert b"\xe6\xb5\x8b\xe8\xaf\x95\xe5\x9b\xa2\xe9\x98\x9f" in serialized_unicode  # UTF-8 encoded Chinese characters

    # Test SubGameConfig
    config = build_sub_game_config(
        game_uid="test_game",
        game_id="test_game:0",
        sub_game_index=0,
        role_for_this_sub_game="police",
        agreed_terms={},
        git_commit="abc123",
    )
    serialized = serialize(config)
    assert serialized == canonical_bytes(config.as_dict())

    # Test SubGameLog
    log = build_sub_game_log(game_uid="test_game", game_id="test_game:0")
    serialized = serialize(log)
    assert serialized == canonical_bytes(log.as_dict())

    # Test SeriesResult
    result = build_series_result(
        game_uid="test_game",
        sub_game_results=[],
        total_police_score=0,
        total_thief_score=0,
        tie_applied=False,
        repo_links={},
        total_llm_tokens_per_series=0,
        sub_game_git_commits={"test_game:0": "abc123"},
        total_llm_tokens_per_sub_game={"test_game:0": 100},
    )
    serialized = serialize(result)
    assert serialized == canonical_bytes(result.as_dict())
