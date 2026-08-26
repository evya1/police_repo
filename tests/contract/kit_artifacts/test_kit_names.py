"""The filename grammar must satisfy the kit's own parser, not merely look right."""

from __future__ import annotations

import re

import pytest

from common.transport import kit_names as names

#: Copied verbatim from the kit's tools/check_artifacts.py. If our names do not match this,
#: the checker does not merely complain -- it does not see the files at all.
KIT_NAME_RE = re.compile(
    r"^(declaration|config|log|result)_(?P<gid>.+?)(?:_g(?P<nn>\d+))?\.json$"
)


@pytest.mark.parametrize("game_id", ["a-vs-b", "team-aleph-vs-team-bet", "zero-one-vs-zero-two"])
def test_match_level_names_carry_no_sub_game_suffix(game_id):
    for name in (names.declaration_name(game_id), names.result_name(game_id)):
        match = KIT_NAME_RE.match(name)
        assert match is not None, name
        assert match.group("gid") == game_id
        assert match.group("nn") is None


@pytest.mark.parametrize("number", [1, 2, 6, 12])
def test_sub_game_names_carry_a_zero_padded_suffix(number):
    for name in (names.config_name("a-vs-b", number), names.log_name("a-vs-b", number)):
        match = KIT_NAME_RE.match(name)
        assert match is not None, name
        assert match.group("gid") == "a-vs-b"
        assert len(match.group("nn")) >= 2
        assert int(match.group("nn")) == number


def test_single_digit_sub_games_are_padded_not_bare():
    assert names.config_name("a-vs-b", 1).endswith("_g01.json")
    assert names.log_name("a-vs-b", 9).endswith("_g09.json")


def test_base_block_carries_join_keys_and_official_schema_version():
    block = names.base_block("a-vs-b", "uid-1")
    assert block["game_id"] == "a-vs-b"
    assert block["game_uid"] == "uid-1"
    assert block["schema_version"] == "1.1"
    assert "schema_profile" not in block


def test_github_links_are_omitted_when_unknown_and_carried_when_given():
    assert "github" not in names.links_block("a-vs-b")
    repos = {"g1": {"cop": "https://example.invalid/c"}}
    assert names.links_block("a-vs-b", repos)["github"] == repos


def test_links_name_all_four_kinds(kit_game_id):
    links = names.links_block(kit_game_id)
    assert links["declaration"] == f"declaration_{kit_game_id}.json"
    assert links["result"] == f"result_{kit_game_id}.json"
    assert links["config"] == f"config_{kit_game_id}_g<NN>.json"
    assert links["log"] == f"log_{kit_game_id}_g<NN>.json"
