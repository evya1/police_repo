"""Group identity: the declaration's per-group block reproduces the kit's own example byte-for-byte.

The reference fixture (tests/fixtures/kit_reference/) is a third-party bundle: nothing here is on
both sides of the digest it carries, so a match proves the construction, not a coincidence.
"""

from __future__ import annotations

import copy

import pytest

from common.transport.kit_identity import (
    GroupIdentity,
    IdentityError,
    group_block,
    hardware_digest,
    verify_group_block,
)


def _identity_from(block: dict) -> GroupIdentity:
    return GroupIdentity(
        group_id=block["group_id"],
        group_name=block["group_name"],
        members=tuple(block["members"]),
        repos=block["repos"],
        mcp_servers=block["mcp_servers"],
        llm_model=block["llm_model"],
        hardware_spec=block["hardware_spec"],
        github_commit=block["github_commit"],
        counted_games_played=block["counted_games_played"],
        code_version=block["code_version"],
    )


def test_group_block_reproduces_the_pinned_declaration_group_key_for_key(kit_declaration):
    reference = kit_declaration["groups"]["group_1"]
    identity = _identity_from(reference)

    assert group_block(identity) == reference


def test_group_block_reproduces_the_second_group_too(kit_declaration):
    reference = kit_declaration["groups"]["group_2"]
    identity = _identity_from(reference)

    assert group_block(identity) == reference


def test_verify_group_block_accepts_the_pinned_block(kit_declaration):
    assert verify_group_block(kit_declaration["groups"]["group_1"]) is True


def test_verify_group_block_rejects_a_one_byte_mutation(kit_declaration):
    mutated = copy.deepcopy(kit_declaration["groups"]["group_1"])
    mutated["code_version"] = mutated["code_version"] + "x"

    assert verify_group_block(mutated) is False


def test_verify_group_block_rejects_a_mutated_signature(kit_declaration):
    mutated = copy.deepcopy(kit_declaration["groups"]["group_1"])
    mutated["signature"] = mutated["signature"][:-1] + ("0" if mutated["signature"][-1] != "0" else "1")

    assert verify_group_block(mutated) is False


def test_verify_group_block_rejects_a_non_block():
    assert verify_group_block({}) is False
    assert verify_group_block("not-a-dict") is False  # type: ignore[arg-type]


def test_hardware_spec_sha256_equals_the_standalone_digest(kit_declaration):
    reference = kit_declaration["groups"]["group_1"]

    assert reference["hardware_spec_sha256"] == hardware_digest(reference["hardware_spec"])


@pytest.mark.parametrize(
    "bad_commit",
    ["", "not-hex", "a" * 39, "a" * 41, "A" * 40, None],
)
def test_a_malformed_github_commit_raises(kit_declaration, bad_commit):
    block = dict(kit_declaration["groups"]["group_1"])
    block["github_commit"] = bad_commit

    with pytest.raises(IdentityError):
        _identity_from(block)


def test_a_negative_counted_games_played_raises(kit_declaration):
    block = dict(kit_declaration["groups"]["group_1"])
    block["counted_games_played"] = -1

    with pytest.raises(IdentityError):
        _identity_from(block)


def test_a_non_int_counted_games_played_raises(kit_declaration):
    block = dict(kit_declaration["groups"]["group_1"])
    block["counted_games_played"] = "0"

    with pytest.raises(IdentityError):
        _identity_from(block)


def test_missing_role_in_repos_raises(kit_declaration):
    block = dict(kit_declaration["groups"]["group_1"])
    block["repos"] = {"cop": block["repos"]["cop"]}

    with pytest.raises(IdentityError):
        _identity_from(block)


def test_missing_role_in_mcp_servers_raises(kit_declaration):
    block = dict(kit_declaration["groups"]["group_1"])
    block["mcp_servers"] = {"thief": block["mcp_servers"]["thief"]}

    with pytest.raises(IdentityError):
        _identity_from(block)


def test_empty_hardware_spec_raises(kit_declaration):
    block = dict(kit_declaration["groups"]["group_1"])
    block["hardware_spec"] = {}

    with pytest.raises(IdentityError):
        _identity_from(block)


def test_empty_members_raises(kit_declaration):
    block = dict(kit_declaration["groups"]["group_1"])
    block["members"] = []

    with pytest.raises(IdentityError):
        _identity_from(block)
