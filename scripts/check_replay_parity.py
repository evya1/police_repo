"""Cross-peer replay parity (T047, RP-11; shared TEST_AND_INTEGRATION_STRATEGY).

Hashes the shared replay source/test files in both trees, then invokes each repository's
own replay CLI as a subprocess in that repository's own working directory. Never imports
the sibling package and never adds it to ``sys.path``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SHARED_DIRS = ("common",)
_SHARED_TEST_FILES = (
    "tests/unit/transport/replay_fixtures.py",
    "tests/unit/transport/test_replay_records.py",
    "tests/unit/transport/test_replay_verify.py",
)


def _hash_tree(root: Path, rel_dir: str) -> dict[str, str]:
    base = root / rel_dir
    return {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(base.rglob("*.py")) if "__pycache__" not in p.parts
    }


def _hash_shared(root: Path) -> dict[str, str]:
    digests: dict[str, str] = {}
    for rel_dir in _SHARED_DIRS:
        digests.update(_hash_tree(root, rel_dir))
    for rel in _SHARED_TEST_FILES:
        path = root / rel
        if path.is_file():
            digests[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return digests


def _compare(ours: dict[str, str], theirs: dict[str, str]) -> list[str]:
    problems = []
    for name in sorted(set(ours) | set(theirs)):
        if name not in theirs:
            problems.append(f"missing in sibling: {name}")
        elif name not in ours:
            problems.append(f"missing locally: {name}")
        elif ours[name] != theirs[name]:
            problems.append(f"digest differs: {name}")
    return problems


def _run(repo_root: Path, script: str, *args: str) -> subprocess.CompletedProcess:
    cmd = ["uv", "run", "python", script, *args]
    return subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True, check=False)


def _reciprocal_check(sibling_root: Path, artifact_root: Path) -> dict:
    """Build one bundle in each repo's own working directory, then cross-verify."""
    ours = _run(_REPO_ROOT, "scripts/smoke_replay_integration.py", "--config", "config/game.json",
                "--artifact-root", str(artifact_root / "ours"), "--json")
    theirs = _run(sibling_root, "scripts/smoke_replay_integration.py", "--config", "config/game.json",
                  "--artifact-root", str(artifact_root / "theirs"), "--json")
    if ours.returncode != 0 or theirs.returncode != 0:
        return {"ok": False, "reason": "smoke build failed", "ours": ours.stderr, "theirs": theirs.stderr}

    our_bundle = json.loads(ours.stdout)["bundle_dir"]
    their_bundle = json.loads(theirs.stdout)["bundle_dir"]
    cross_a = _run(sibling_root, "scripts/replay.py", our_bundle, "--json")
    cross_b = _run(_REPO_ROOT, "scripts/replay.py", their_bundle, "--json")
    return {
        "ok": cross_a.returncode == 0 and cross_b.returncode == 0,
        "sibling_verified_our_bundle": cross_a.returncode,
        "we_verified_sibling_bundle": cross_b.returncode,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Cross-peer replay parity (T047, RP-11).")
    parser.add_argument("--sibling-root", required=True, type=Path)
    parser.add_argument("--bundle-from-each", action="store_true")
    parser.add_argument("--artifact-root", type=Path, default=Path("/tmp/replay-parity"))
    args = parser.parse_args(argv)

    sibling_root = args.sibling_root.resolve()
    hash_problems = _compare(_hash_shared(_REPO_ROOT), _hash_shared(sibling_root))
    report: dict = {"shared_hash_problems": hash_problems}

    if hash_problems:
        print(json.dumps(report, indent=2, sort_keys=True))
        return 1

    if args.bundle_from_each:
        report["reciprocal"] = _reciprocal_check(sibling_root, args.artifact_root)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["reciprocal"]["ok"] else 1

    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
