"""Identity is declared, never guessed at, and the greeting extension never refuses."""

from __future__ import annotations

import hashlib

import pytest

from common.transport.canonical import canonical_bytes
from common.transport.kit_identity import (
    GREETING_KEYS,
    SIGNATURE_PREFIX,
    GroupIdentity,
    IdentityError,
    config_digest,
    group_block,
    hardware_digest,
    identity_from_greeting,
    identity_greeting_block,
    verify_group_block,
)
from common.transport.negotiate import our_greeting, verify_greeting
from common.transport.terms import project_terms

COMMIT = "a1ef0000c0fc0fc0fc0fc0fc0fc0fc0fc0fc0f5c"
HARDWARE = {"os": "Linux", "cpu_cores": 8, "ram_gb": 16}


def an_identity(**overrides) -> GroupIdentity:
    base = {
        "group_id": "zeroone", "group_name": "ZeroOne", "members": ("id-1001", "id-1002"),
        "repos": {"cop": "https://example.invalid/p", "thief": "https://example.invalid/t"},
        "mcp_servers": {"cop": "https://a.invalid/mcp", "thief": "https://b.invalid/mcp"},
        "llm_model": "template", "hardware_spec": HARDWARE, "github_commit": COMMIT,
        "counted_games_played": 0, "code_version": "1.0.0",
    }
    return GroupIdentity(**{**base, **overrides})


# --- nothing is invented -------------------------------------------------------------------


@pytest.mark.parametrize("field", ["group_id", "group_name", "llm_model", "code_version"])
def test_a_missing_scalar_raises_by_name(field):
    with pytest.raises(IdentityError, match=field):
        an_identity(**{field: ""})


def test_members_are_required():
    with pytest.raises(IdentityError, match="members"):
        an_identity(members=())


@pytest.mark.parametrize("field", ["repos", "mcp_servers"])
def test_both_roles_must_be_named(field):
    with pytest.raises(IdentityError, match="both roles"):
        an_identity(**{field: {"cop": "https://example.invalid/only"}})


def test_hardware_is_required_for_the_fairness_declaration():
    with pytest.raises(IdentityError, match="hardware_spec"):
        an_identity(hardware_spec={})


@pytest.mark.parametrize("bad", ["", "not-a-sha", "A1EF0000C0FC0FC0FC0FC0FC0FC0FC0FC0FC0F5C", COMMIT[:39]])
def test_the_commit_must_be_a_forty_character_hex_sha(bad):
    with pytest.raises(IdentityError, match="github_commit"):
        an_identity(github_commit=bad)


def test_a_negative_game_count_is_refused():
    with pytest.raises(IdentityError, match="negative"):
        an_identity(counted_games_played=-1)


# --- sign-then-insert ----------------------------------------------------------------------


def test_the_signature_covers_the_block_before_it_existed():
    block = group_block(an_identity())
    unsigned = {k: v for k, v in block.items() if k != "signature"}
    expected = SIGNATURE_PREFIX + hashlib.sha256(canonical_bytes(unsigned)).hexdigest()
    assert block["signature"] == expected
    assert verify_group_block(block)


def test_a_one_byte_mutation_breaks_the_signature():
    block = group_block(an_identity())
    block["group_name"] = "ZeroTwo"
    assert not verify_group_block(block)


def test_a_block_with_no_signature_does_not_verify():
    assert not verify_group_block({"group_id": "a"})
    assert not verify_group_block({"group_id": "a", "signature": "deadbeef"})


def test_the_hardware_digest_is_the_canonical_hash():
    block = group_block(an_identity())
    assert block["hardware_spec_sha256"] == hardware_digest(HARDWARE)
    assert hardware_digest(HARDWARE) == hashlib.sha256(canonical_bytes(HARDWARE)).hexdigest()


def test_the_config_digest_is_the_canonical_hash_of_the_terms():
    terms = {"board_size": 7, "num_games": 6}
    assert config_digest(terms) == hashlib.sha256(canonical_bytes(terms)).hexdigest()


# --- what rides the wire -------------------------------------------------------------------


def test_the_greeting_carries_the_complete_signed_identity():
    block = identity_greeting_block(an_identity())
    assert set(block) == set(GREETING_KEYS)
    assert block["hardware_spec"] == HARDWARE
    assert block["hardware_spec_sha256"] == hardware_digest(HARDWARE)
    assert verify_group_block(block)


def test_an_opponent_that_declares_nothing_is_not_a_fault():
    assert identity_from_greeting({}) is None
    assert identity_from_greeting({"identity": "not-a-block"}) is None
    assert identity_from_greeting({"identity": {"role": "thief"}}) is None


def test_an_opponents_partial_declaration_is_read_as_far_as_it_goes():
    read = identity_from_greeting({"identity": {"group_id": "them", "llm_model": "template"}})
    assert read == {"group_id": "them", "llm_model": "template"}


# --- the extension is additive ---------------------------------------------------------------


def _terms() -> dict:
    from pathlib import Path

    from common.config import load_config

    shared = load_config(Path(__file__).resolve().parents[3] / "config" / "game.json")
    return project_terms(shared, {})


def test_a_greeting_without_an_identity_block_is_unchanged():
    terms = _terms()
    plain = our_greeting(terms, "n" * 32, "us", "police", 1)
    assert plain["identity"] == {"group_id": "us", "role": "police"}


def test_an_identity_block_rides_along_without_displacing_the_core_keys():
    terms = _terms()
    block = identity_greeting_block(an_identity())
    greeting = our_greeting(terms, "n" * 32, "us", "police", 1, identity_block=block)
    assert greeting["identity"]["group_id"] == "us", "the core keys always win"
    assert greeting["identity"]["role"] == "police"
    assert greeting["identity"]["llm_model"] == "template"


def test_verify_greeting_never_refuses_over_an_identity_block():
    """An opponent who says more, less, or something unknown must still be playable."""
    terms = _terms()
    block = identity_greeting_block(an_identity(group_id="them"))
    for extra in ({}, block, {**block, "unknown_future_key": "whatever"}):
        raw = our_greeting(terms, "n" * 32, "them", "thief", 1, identity_block=extra)
        agreed = verify_greeting(raw, terms, "us", 1)
        assert agreed.opponent_group == "them"
