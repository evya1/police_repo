"""Counted play refuses on missing evidence, by name, before a game exists."""

from __future__ import annotations

import textwrap

import pytest

from police_peer.evidence.token_ledger import TokenLedger
from police_peer.evidence.tokens import TokenEvent, UsageStatus
from police_peer.league.readiness import CountedPlayNotReadyError, assert_counted_ready
from police_peer.wire.config import load_private

TERMS = {"board_size": 7, "num_games": 6}
FULL_TOML = """
    [game]
    group_name = "ZeroOne"
    group_id = "zeroone"
    members = ["id-1001", "id-1002"]
    repos = { cop = "https://example.invalid/p", thief = "https://example.invalid/t" }
    [network]
    public_url = "https://tunnel.invalid/mcp"
    [llm]
    model = "template"
"""


def private_from(tmp_path, body: str):
    path = tmp_path / "game.toml"
    path.write_text(textwrap.dedent(body), encoding="utf-8")
    return load_private(path)


def ready(tmp_path, body: str = FULL_TOML, **overrides):
    kwargs = {
        "group_id": "zeroone", "repo_root": ".", "code_version": "1.0.0",
        "terms": TERMS, "group_code_confirmed": True, "ledger": TokenLedger(),
    }
    kwargs.update(overrides)
    return assert_counted_ready(private_from(tmp_path, body), **kwargs)


def test_a_complete_declaration_is_allowed_to_play(tmp_path):
    resolved = ready(tmp_path)
    assert resolved.identity.group_name == "ZeroOne"
    assert len(resolved.config_digest) == 64


def test_an_unconfirmed_team_code_refuses(tmp_path):
    with pytest.raises(CountedPlayNotReadyError, match="eight-character team code"):
        ready(tmp_path, group_code_confirmed=False)


def test_a_missing_repository_link_refuses_naming_it(tmp_path):
    body = FULL_TOML.replace(
        'repos = { cop = "https://example.invalid/p", thief = "https://example.invalid/t" }',
        'repos = { cop = "https://example.invalid/p" }',
    )
    with pytest.raises(CountedPlayNotReadyError, match="thief"):
        ready(tmp_path, body)


def test_a_missing_public_address_refuses_naming_it(tmp_path):
    body = FULL_TOML.replace('public_url = "https://tunnel.invalid/mcp"', "")
    with pytest.raises(CountedPlayNotReadyError, match="public MCP address"):
        ready(tmp_path, body)


def test_opponent_url_is_never_claimed_as_our_public_address(tmp_path):
    body = FULL_TOML.replace(
        'public_url = "https://tunnel.invalid/mcp"',
        'opponent_url = "https://opponent.invalid/mcp"',
    )
    with pytest.raises(CountedPlayNotReadyError, match="public MCP address"):
        ready(tmp_path, body)


def test_missing_members_refuse(tmp_path):
    body = FULL_TOML.replace('members = ["id-1001", "id-1002"]', "members = []")
    with pytest.raises(CountedPlayNotReadyError, match="members"):
        ready(tmp_path, body)


def test_a_missing_group_name_refuses(tmp_path):
    body = FULL_TOML.replace('group_name = "ZeroOne"', 'group_name = ""')
    with pytest.raises(CountedPlayNotReadyError, match="group_name"):
        ready(tmp_path, body)


def test_an_unreadable_commit_refuses(tmp_path):
    with pytest.raises(CountedPlayNotReadyError, match="commit at HEAD"):
        ready(tmp_path, repo_root=tmp_path)


def test_absent_terms_refuse_because_no_digest_can_be_computed(tmp_path):
    with pytest.raises(CountedPlayNotReadyError, match="configuration digest"):
        ready(tmp_path, terms={})


def test_unknown_token_usage_refuses(tmp_path):
    """The report declares total tokens consumed; an unknown total cannot be declared honestly."""
    ledger = TokenLedger()
    ledger.record(TokenEvent(
        sub_game_id="1", step=1, counted=True, provider_called=True, fallback=False,
        status=UsageStatus.UNKNOWN, input_tokens=None, output_tokens=None,
    ))
    with pytest.raises(CountedPlayNotReadyError, match="UNKNOWN"):
        ready(tmp_path, ledger=ledger)


def test_missing_token_accounting_refuses(tmp_path):
    with pytest.raises(CountedPlayNotReadyError, match="accounting is unavailable"):
        ready(tmp_path, ledger=None)


def test_a_clean_ledger_does_not_refuse(tmp_path):
    ledger = TokenLedger()
    ledger.record(TokenEvent(
        sub_game_id="1", step=1, counted=True, provider_called=False, fallback=False,
        status=UsageStatus.KNOWN_ZERO, input_tokens=0, output_tokens=0,
    ))
    assert ready(tmp_path, ledger=ledger).identity.llm_model == "template"
