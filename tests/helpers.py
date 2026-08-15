"""Small helpers shared by standard-library-compatible tests."""

from __future__ import annotations

import contextlib
import io
import subprocess
from collections.abc import Callable
from pathlib import Path


def initialize_git_repository(path: Path) -> Path:
    """Create an empty Git worktree."""
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    return path


def track(repo: Path, *relative_paths: str) -> None:
    """Add selected paths to the temporary repository index."""
    subprocess.run(["git", "-C", str(repo), "add", "--", *relative_paths], check=True)


def captured_main(function: Callable[[list[str]], int], arguments: list[str]) -> tuple[int, str]:
    """Run a gate main function and capture both output streams."""
    output = io.StringIO()
    with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
        result = function(arguments)
    return result, output.getvalue()
