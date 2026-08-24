"""The exact commit that played, read without a subprocess (App. E rule 53).

Shelling out to ``git`` would make evidence collection depend on the ``git`` binary being on
PATH inside whatever sandbox runs the peer, and would make a fabricated ``GIT_DIR``/env trivial
to inject. Reading the two or three small files under ``.git`` directly has no such dependency
and no such surface.
"""

from __future__ import annotations

from pathlib import Path

_HEAD_REF_PREFIX = "ref: "


class MissingGitRevisionError(Exception):
    """No commit could be determined for this repository -- nothing is guessed."""


def _resolve_ref(git_dir: Path, ref: str) -> str | None:
    """Resolve one ref (e.g. ``refs/heads/main``) to a commit, loose file first, then packed."""
    loose = git_dir / ref
    if loose.is_file():
        value = loose.read_text(encoding="utf-8").strip()
        return value or None

    packed = git_dir / "packed-refs"
    if packed.is_file():
        for line in packed.read_text(encoding="utf-8").splitlines():
            if not line or line.startswith("#") or line.startswith("^"):
                continue
            sha, _, packed_ref = line.partition(" ")
            if packed_ref == ref:
                return sha or None
    return None


def head_commit(repo_root: Path) -> str | None:
    """Return the 40-hex commit HEAD points to, or ``None`` when it cannot be determined.

    Handles a detached HEAD (``.git/HEAD`` holds the sha directly), a symbolic ref (``HEAD``
    points at ``refs/heads/<branch>``, resolved as a loose file), and a packed-refs-only repo
    (the branch has no loose ref file because it was packed by ``git gc``).
    """
    git_dir = repo_root / ".git"
    head_path = git_dir / "HEAD"
    if not head_path.is_file():
        return None

    contents = head_path.read_text(encoding="utf-8").strip()
    if contents.startswith(_HEAD_REF_PREFIX):
        ref = contents[len(_HEAD_REF_PREFIX):].strip()
        return _resolve_ref(git_dir, ref)

    # Detached HEAD: the file holds the commit sha directly.
    return contents or None


def require_head_commit(repo_root: Path) -> str:
    """Return the HEAD commit, or raise a named error when it cannot be determined."""
    commit = head_commit(repo_root)
    if commit is None:
        raise MissingGitRevisionError(
            f"no git HEAD commit could be determined under {repo_root} -- App. E rule 53 "
            f"requires the exact commit that played, and none is invented"
        )
    return commit
