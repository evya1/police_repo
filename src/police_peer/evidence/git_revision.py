"""The commit that actually played, read from `.git` without invoking git (App. E rule 53).

Every counted game must record the exact commit its code ran from, so a grader can reproduce
the version that competed rather than whatever the branch looks like later. Code may change
between games; the recorded sha may not be approximate.

This reads the repository's own files rather than shelling out. Not for speed: a subprocess
here would inherit the caller's environment and working directory, and would be one more thing
that can hang inside a turn budget. Reading two small files cannot.

An unreadable or absent repository returns None. The refusal belongs to counted play, not to
this reader -- a warm-up in an exported tarball is a legitimate thing to run.
"""

from __future__ import annotations

import re
from pathlib import Path

_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


class MissingGitRevisionError(Exception):
    """A counted game needs the commit that played, and it could not be determined."""


def _read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError):
        return None


def _from_packed_refs(git_dir: Path, ref: str) -> str | None:
    """Resolve a ref that has been packed away by `git gc` -- the common case on a fresh clone."""
    packed = _read(git_dir / "packed-refs")
    if packed is None:
        return None
    for line in packed.splitlines():
        if line.startswith(("#", "^")):
            continue
        parts = line.split(maxsplit=1)
        if len(parts) == 2 and parts[1].strip() == ref and _SHA_RE.match(parts[0]):
            return parts[0]
    return None


def head_commit(repo_root: Path | str) -> str | None:
    """Return the 40-hex sha at HEAD, or None when it cannot be determined."""
    git_dir = Path(repo_root) / ".git"
    if git_dir.is_file():
        # A worktree or submodule: .git is a file pointing at the real directory.
        pointer = _read(git_dir)
        if not pointer or not pointer.startswith("gitdir:"):
            return None
        git_dir = Path(pointer.split(":", 1)[1].strip())
    head = _read(git_dir / "HEAD")
    if head is None:
        return None
    if _SHA_RE.match(head):
        return head  # detached HEAD
    if not head.startswith("ref:"):
        return None
    ref = head.split(":", 1)[1].strip()
    direct = _read(git_dir / ref)
    if direct and _SHA_RE.match(direct):
        return direct
    return _from_packed_refs(git_dir, ref)


def require_head_commit(repo_root: Path | str) -> str:
    """Return the commit that played, or refuse by name."""
    sha = head_commit(repo_root)
    if sha is None:
        raise MissingGitRevisionError(
            f"cannot determine the commit at HEAD under {repo_root}. A counted game records "
            f"the exact commit that played (App. E rule 53), and an approximate one is worse "
            f"than none: it would send a grader to code that never competed"
        )
    return sha
