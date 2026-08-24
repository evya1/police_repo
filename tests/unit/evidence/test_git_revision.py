"""Reading the commit that played, from the repository's own files and never a subprocess."""

from __future__ import annotations

import pytest

from police_peer.evidence.git_revision import (
    MissingGitRevisionError,
    head_commit,
    require_head_commit,
)

SHA = "a1ef0000c0fc0fc0fc0fc0fc0fc0fc0fc0fc0f5c"
OTHER = "b2e70000abcabcabcabcabcabcabcabcabcabc90"


def make_repo(tmp_path, head: str, refs: dict[str, str] | None = None, packed: str = ""):
    git = tmp_path / ".git"
    (git / "refs" / "heads").mkdir(parents=True)
    (git / "HEAD").write_text(head, encoding="utf-8")
    for name, sha in (refs or {}).items():
        path = git / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(sha + "\n", encoding="utf-8")
    if packed:
        (git / "packed-refs").write_text(packed, encoding="utf-8")
    return tmp_path


def test_a_symbolic_head_resolves_through_its_ref(tmp_path):
    repo = make_repo(tmp_path, "ref: refs/heads/main\n", {"refs/heads/main": SHA})
    assert head_commit(repo) == SHA


def test_a_detached_head_is_read_directly(tmp_path):
    assert head_commit(make_repo(tmp_path, SHA + "\n")) == SHA


def test_a_packed_ref_resolves_when_no_loose_ref_exists(tmp_path):
    """The common case on a fresh clone, where git gc has packed the refs away."""
    repo = make_repo(
        tmp_path, "ref: refs/heads/main\n",
        packed=f"# pack-refs with: peeled fully-peeled sorted\n{SHA} refs/heads/main\n",
    )
    assert head_commit(repo) == SHA


def test_a_loose_ref_wins_over_a_stale_packed_one(tmp_path):
    repo = make_repo(
        tmp_path, "ref: refs/heads/main\n", {"refs/heads/main": SHA},
        packed=f"{OTHER} refs/heads/main\n",
    )
    assert head_commit(repo) == SHA


def test_peeled_annotated_tag_lines_are_skipped(tmp_path):
    repo = make_repo(
        tmp_path, "ref: refs/heads/main\n",
        packed=f"{OTHER} refs/tags/v1\n^{SHA}\n{SHA} refs/heads/main\n",
    )
    assert head_commit(repo) == SHA


def test_a_git_file_pointer_is_followed(tmp_path):
    """A worktree or submodule: .git is a file naming the real directory."""
    real = tmp_path / "real"
    (real / "refs" / "heads").mkdir(parents=True)
    (real / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (real / "refs" / "heads" / "main").write_text(SHA + "\n", encoding="utf-8")
    work = tmp_path / "work"
    work.mkdir()
    (work / ".git").write_text(f"gitdir: {real}\n", encoding="utf-8")
    assert head_commit(work) == SHA


def test_a_directory_that_is_not_a_repository_yields_none(tmp_path):
    assert head_commit(tmp_path) is None


def test_an_unresolvable_ref_yields_none(tmp_path):
    assert head_commit(make_repo(tmp_path, "ref: refs/heads/missing\n")) is None


def test_a_garbage_head_yields_none(tmp_path):
    assert head_commit(make_repo(tmp_path, "not a ref at all\n")) is None


def test_requiring_a_commit_refuses_by_name_rather_than_guessing(tmp_path):
    with pytest.raises(MissingGitRevisionError, match="commit at HEAD"):
        require_head_commit(tmp_path)


def test_no_subprocess_is_ever_spawned(tmp_path, monkeypatch):
    """A subprocess here would inherit the caller's cwd and could hang inside a turn budget."""
    import subprocess

    def explode(*args, **kwargs):
        raise AssertionError("git_revision must not shell out")

    monkeypatch.setattr(subprocess, "run", explode)
    monkeypatch.setattr(subprocess, "check_output", explode)
    monkeypatch.setattr(subprocess, "Popen", explode)
    repo = make_repo(tmp_path, "ref: refs/heads/main\n", {"refs/heads/main": SHA})
    assert head_commit(repo) == SHA
