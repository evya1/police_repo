"""HEAD commit resolution without a subprocess (App. E rule 53)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from police_peer.evidence.git_revision import (
    MissingGitRevisionError,
    head_commit,
    require_head_commit,
)

COMMIT = "a" * 40


def _no_subprocess(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(*args, **kwargs):
        raise AssertionError("git_revision must never spawn a subprocess")

    monkeypatch.setattr(subprocess, "run", _boom)
    monkeypatch.setattr(subprocess, "Popen", _boom)


def test_detached_head(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _no_subprocess(monkeypatch)
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "HEAD").write_text(COMMIT + "\n", encoding="utf-8")

    assert head_commit(tmp_path) == COMMIT
    assert require_head_commit(tmp_path) == COMMIT


def test_symbolic_ref_loose_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _no_subprocess(monkeypatch)
    git_dir = tmp_path / ".git"
    (git_dir / "refs" / "heads").mkdir(parents=True)
    (git_dir / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (git_dir / "refs" / "heads" / "main").write_text(COMMIT + "\n", encoding="utf-8")

    assert head_commit(tmp_path) == COMMIT


def test_symbolic_ref_packed_refs_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _no_subprocess(monkeypatch)
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (git_dir / "packed-refs").write_text(
        f"# pack-refs with: peeled fully-peeled sorted\n{COMMIT} refs/heads/main\n",
        encoding="utf-8",
    )

    assert head_commit(tmp_path) == COMMIT


def test_non_repo_directory_returns_none(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _no_subprocess(monkeypatch)

    assert head_commit(tmp_path) is None
    with pytest.raises(MissingGitRevisionError):
        require_head_commit(tmp_path)


def test_dangling_symbolic_ref_returns_none(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _no_subprocess(monkeypatch)
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "HEAD").write_text("ref: refs/heads/nonexistent\n", encoding="utf-8")

    assert head_commit(tmp_path) is None
