"""T016 repair tests — recursive secret detection (AC4), git_commit determinism (AC3),
and deterministic internal filenames (AC3). INTERNAL CONTRACT — NOT OFFICIAL TEMPLATE CONFORMANCE.
"""

from __future__ import annotations

import pytest

from police_peer.reporting.schemas import (
    SchemaError,
    artifact_filename,
    build_declaration,
    build_series_result,
    build_sub_game_config,
    build_sub_game_log,
    validate_schema,
)


def _base_declaration():
    return build_declaration(
        game_uid="test_game",
        team="t",
        role="police",
        members=[],
        police_repo_url="http://example.com",
        thief_repo_url="http://example.com",
        mcp_addresses=[],
        hardware="h",
        model="m",
        token_budget=100,
        start_time="s",
        end_time="e",
    )


def test_recursive_secret_in_agreed_terms_rejected():
    config = build_sub_game_config(
        game_uid="test_game",
        game_id="test_game:0",
        sub_game_index=0,
        role_for_this_sub_game="police",
        agreed_terms={"api_key": "super-secret-value"},
        git_commit="abc123",
    )
    with pytest.raises(SchemaError):
        validate_schema(config)


def test_recursive_secret_in_sub_game_results_rejected():
    result = build_series_result(
        game_uid="test_game",
        sub_game_results=[{"game_id": "test_game:0", "refresh_token": "tok"}],
        total_police_score=0,
        total_thief_score=0,
        tie_applied=False,
        repo_links={},
        total_llm_tokens_per_series=0,
    )
    with pytest.raises(SchemaError):
        validate_schema(result)


def test_git_commit_must_be_non_empty():
    with pytest.raises(SchemaError):
        build_sub_game_config(
            game_uid="test_game",
            game_id="test_game:0",
            sub_game_index=0,
            role_for_this_sub_game="police",
            agreed_terms={},
            git_commit="",
        )


def test_artifact_filename_deterministic_and_replayable():
    config = build_sub_game_config(
        game_uid="test_game",
        game_id="test_game:0",
        sub_game_index=0,
        role_for_this_sub_game="police",
        agreed_terms={},
        git_commit="abc123",
    )
    expected = "sub_game_config_test_game_test_game:0.json"
    assert artifact_filename(config) == expected
    # replayable: same artifact -> same filename
    assert artifact_filename(config) == expected

    declaration = _base_declaration()
    assert artifact_filename(declaration) == "declaration_test_game_series.json"

    log = build_sub_game_log(game_uid="test_game", game_id="test_game:0")
    assert artifact_filename(log) == "log_test_game_test_game:0.json"


def test_clean_artifacts_pass_secret_scan():
    # A clean config with non-secret agreed_terms must pass schema validation.
    config = build_sub_game_config(
        game_uid="test_game",
        game_id="test_game:0",
        sub_game_index=0,
        role_for_this_sub_game="police",
        agreed_terms={"max_moves": 35, "map_area": "New York"},
        git_commit="abc123",
    )
    validate_schema(config)  # must not raise
