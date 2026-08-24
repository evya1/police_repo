"""Every missing identity field raises its own named error; nothing is defaulted (DEC-12)."""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from common.config import PrivateConfig
from police_peer.evidence.identity_source import (
    IdentitySourceError,
    build_identity,
)

COMMIT = "b" * 40


def _repo(tmp_path: Path) -> Path:
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "HEAD").write_text(COMMIT + "\n", encoding="utf-8")
    return tmp_path


def _complete_private() -> PrivateConfig:
    return PrivateConfig(
        group_name="Team A",
        members=("Alice", "Bob"),
        repos={"cop": "https://github.com/a/cop", "thief": "https://github.com/a/thief"},
        mcp_servers={"cop": "https://cop.a.example/mcp", "thief": "https://thief.a.example/mcp"},
        llm_model="template",
    )


def test_a_complete_private_config_builds_a_valid_identity(tmp_path: Path) -> None:
    identity = build_identity(
        _complete_private(),
        group_id="team-a",
        repo_root=_repo(tmp_path),
        code_version="1.00",
        counted_games_played=3,
    )

    assert identity.group_id == "team-a"
    assert identity.github_commit == COMMIT
    assert identity.counted_games_played == 3


@pytest.mark.parametrize(
    ("field_to_clear", "empty_value", "expected_snippet"),
    [
        ("group_name", None, "group_name"),
        ("members", (), "members"),
        ("repos", {}, "repos"),
        ("mcp_servers", {}, "mcp_servers"),
        ("llm_model", None, "llm"),
    ],
)
def test_each_missing_required_field_raises_its_own_named_error(
    tmp_path: Path, field_to_clear: str, empty_value: object, expected_snippet: str
) -> None:
    private = dataclasses.replace(_complete_private(), **{field_to_clear: empty_value})

    with pytest.raises(IdentitySourceError, match=expected_snippet):
        build_identity(
            private,
            group_id="team-a",
            repo_root=_repo(tmp_path),
            code_version="1.00",
            counted_games_played=0,
        )


def test_a_missing_git_commit_raises(tmp_path: Path) -> None:
    with pytest.raises(IdentitySourceError, match="git"):
        build_identity(
            _complete_private(),
            group_id="team-a",
            repo_root=tmp_path,  # no .git at all
            code_version="1.00",
            counted_games_played=0,
        )


def test_nothing_is_defaulted_to_a_placeholder(tmp_path: Path) -> None:
    """A GroupIdentity built here always carries the real repo_root commit, never a stand-in."""
    identity = build_identity(
        _complete_private(),
        group_id="team-a",
        repo_root=_repo(tmp_path),
        code_version="1.00",
        counted_games_played=0,
    )

    assert identity.github_commit != "0" * 40
    assert identity.hardware_spec  # real collect_runtime_summary() output, never empty
