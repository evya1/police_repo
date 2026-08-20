import pytest

from police_peer.reporting.schemas import (
    FinalizedLogMutationError,
    SchemaError,
    SignatureError,
    assert_lifecycle_ok,
    build_declaration,
    build_series_result,
    build_sub_game_config,
    build_sub_game_log,
    finalize_log,
    verify_artifact,
)


def _sample_signer(nonce: str = "test_nonce"):
    def signer(data: bytes) -> str:
        import hashlib
        return hashlib.sha256(data + nonce.encode("utf-8")).hexdigest()
    return signer


def _sample_verifier(nonce: str = "test_nonce"):
    def verifier(data: bytes, signature: str) -> bool:
        import hashlib
        expected = hashlib.sha256(data + nonce.encode("utf-8")).hexdigest()
        return signature == expected
    return verifier


def test_artifact_lifecycle():
    # Test valid lifecycle stages
    declaration = build_declaration(
        game_uid="test_game",
        team="test_team",
        role="police",
        members=["alice", "bob"],
        police_repo_url="http://example.com/police",
        thief_repo_url="http://example.com/thief",
        mcp_addresses=["mcp://1.1.1.1:8000"],
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
        agreed_terms={"max_moves": 30},
        git_commit="abc1234",
    )
    assert_lifecycle_ok(config, "pre_sub_game")

    log = build_sub_game_log(game_uid="test_game", game_id="test_game:0")
    assert_lifecycle_ok(log, "during_sub_game")
    assert_lifecycle_ok(log, "pre_sub_game")

    result = build_series_result(
        game_uid="test_game",
        sub_game_results=[{"game_id": "test_game:0", "score": 10}],
        total_police_score=10,
        total_thief_score=5,
        tie_applied=False,
        repo_links={"police": "http://example.com/police"},
        total_llm_tokens_per_series=500,
        sub_game_git_commits={"test_game:0": "abc1234"},
        total_llm_tokens_per_sub_game={"test_game:0": 500},
    )
    assert_lifecycle_ok(result, "post_settlement")

    # Test invalid lifecycle stages
    with pytest.raises(SchemaError, match="pre_series"):
        assert_lifecycle_ok(declaration, "post_settlement")

    with pytest.raises(SchemaError, match="pre_sub_game"):
        assert_lifecycle_ok(config, "pre_series")

    with pytest.raises(SchemaError, match="pre_sub_game or during_sub_game"):
        assert_lifecycle_ok(log, "post_settlement")

    with pytest.raises(SchemaError, match="post_settlement"):
        assert_lifecycle_ok(result, "pre_series")

    with pytest.raises(SchemaError, match="Invalid lifecycle stage"):
        assert_lifecycle_ok(declaration, "invalid_stage")


def test_real_subgame_log_lifecycle_and_verification():
    # 1. Construct log
    log = build_sub_game_log(game_uid="test_game", game_id="test_game:0")
    assert not log.finalized
    assert log.signature is None
    assert log.steps == []

    # 2. Mutate while legal
    log.steps.append({"step_index": 0, "action": "scan"})
    log.steps.append({"step_index": 1, "action": "move"})
    assert len(log.steps) == 2

    # 3. Finalize log using signer
    signer = _sample_signer("test_nonce")
    verifier = _sample_verifier("test_nonce")

    finalized_log = finalize_log(log, signer)
    assert finalized_log is log
    assert log.finalized is True
    assert log.signature is not None
    assert isinstance(log.signature, str)

    # 4. Verify that the stored signature verifies against the finalized log
    assert verify_artifact(log, log.signature, verifier) is True

    # 5. Calling finalize_log on an already-finalized log raises FinalizedLogMutationError
    with pytest.raises(FinalizedLogMutationError, match="already finalized"):
        finalize_log(log, signer)

    # 6. Immutability checks: all fields must be protected from mutation
    with pytest.raises(FinalizedLogMutationError):
        log.steps = []

    with pytest.raises(FinalizedLogMutationError):
        log.finalized = False

    with pytest.raises(FinalizedLogMutationError):
        log.signature = "tampered_sig"

    with pytest.raises(FinalizedLogMutationError):
        log.game_uid = "other_uid"

    with pytest.raises(FinalizedLogMutationError):
        log.game_id = "other_id"

    with pytest.raises(FinalizedLogMutationError):
        log.schema_version = "other_version"

    with pytest.raises(FinalizedLogMutationError):
        log.kind = "other_kind"


def test_finalize_log_signer_none():
    log = build_sub_game_log(game_uid="test_game", game_id="test_game:0")
    with pytest.raises(SignatureError, match="Signer cannot be None"):
        finalize_log(log, None)
    assert not log.finalized
