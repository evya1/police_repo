import pytest

from police_peer.reporting.schemas import (
    IdentifierMismatchError,
    SchemaError,
    SignatureError,
    _validate_field_types,
    build_declaration,
    build_series_result,
    build_sub_game_config,
    build_sub_game_log,
    sign_artifact,
    validate_identifiers,
    validate_schema,
    verify_artifact,
)


def _make_decl(game_uid: str = "test_game", num_games: int = 6):
    return build_declaration(
        game_uid=game_uid, team="t", role="police", members=["a"],
        police_repo_url="http://p", thief_repo_url="http://t",
        mcp_addresses=["mcp://1"], hardware="h", model="m",
        token_budget=100, start_time="s", end_time="e", num_games=num_games,
    )


def test_validate_field_types_tuples_and_presence():
    spec = {"s": str, "i": int, "opt": (str, type(None)), "l": list}
    valid = {"s": "ok", "i": 1, "opt": None, "l": []}
    _validate_field_types(valid, spec)
    _validate_field_types(dict(valid, opt="set"), spec)

    with pytest.raises(SchemaError, match="Field 'opt' must be one of"):
        _validate_field_types(dict(valid, opt=99), spec)
    with pytest.raises(SchemaError, match="Required field 'l' is missing"):
        _validate_field_types({"s": "ok", "i": 1, "opt": None}, spec)
    with pytest.raises(SchemaError, match="Disallowed extra field"):
        _validate_field_types(dict(valid, extra=1), spec)
    with pytest.raises(SchemaError, match="Field 'i' must be of type int"):
        _validate_field_types(dict(valid, i="bad"), spec)


def test_validate_schema_declarations_and_series():
    decl = _make_decl()
    validate_schema(decl)
    decl.num_games = -1
    with pytest.raises(SchemaError, match="num_games"):
        validate_schema(decl)

    cfg = build_sub_game_config(
        game_uid="test_game", game_id="g:0", sub_game_index=0,
        role_for_this_sub_game="police", agreed_terms={"seed": 1}, git_commit="abc",
    )
    validate_schema(cfg)

    log = build_sub_game_log(game_uid="test_game", game_id="g:0")
    validate_schema(log)
    log.signature = "sig"
    validate_schema(log)

    res = build_series_result(
        game_uid="test_game", sub_game_results=[{"game_id": "g:0", "score": 10}],
        total_police_score=10, total_thief_score=5, tie_applied=False,
        repo_links={"police": "http://p"}, total_llm_tokens_per_series=500,
        sub_game_git_commits={"g:0": "abc"}, total_llm_tokens_per_sub_game={"g:0": 500},
    )
    validate_schema(res)
    assert res.sub_game_git_commits == {"g:0": "abc"}
    assert res.total_llm_tokens_per_sub_game == {"g:0": 500}


def test_signature_error_none_signer_verifier():
    decl = _make_decl()
    with pytest.raises(SignatureError, match="Signer cannot be None"):
        sign_artifact(decl, None)
    with pytest.raises(SignatureError, match="Verifier cannot be None"):
        verify_artifact(decl, "sig", None)


def test_validate_identifiers_suite():
    decl = _make_decl("test_game")
    cfg = build_sub_game_config(
        game_uid="test_game", game_id="g:0", sub_game_index=0,
        role_for_this_sub_game="police", agreed_terms={}, git_commit="abc",
    )
    log = build_sub_game_log(game_uid="test_game", game_id="g:0")
    res = build_series_result(
        game_uid="test_game", sub_game_results=[], total_police_score=0,
        total_thief_score=0, tie_applied=False, repo_links={}, total_llm_tokens_per_series=0,
    )

    validate_identifiers()
    validate_identifiers(decl)
    validate_identifiers(decl, cfg, log, res)

    diff_uid = build_sub_game_config(
        game_uid="other", game_id="g:0", sub_game_index=0,
        role_for_this_sub_game="police", agreed_terms={}, git_commit="abc",
    )
    with pytest.raises(IdentifierMismatchError, match="Mismatched game_uid"):
        validate_identifiers(decl, diff_uid)

    diff_id = build_sub_game_log(game_uid="test_game", game_id="g:1")
    with pytest.raises(IdentifierMismatchError, match="Mismatched game_id"):
        validate_identifiers(cfg, diff_id)
