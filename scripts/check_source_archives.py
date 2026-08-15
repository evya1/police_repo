"""Reject tracked source archives unless explicitly allowlisted."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from quality_common import QualityError, load_config, repository_root, string_list, tracked_files


def unexpected_archives(repo: Path, config: dict[str, object]) -> list[str]:
    """Return tracked archive paths not present in the allowlist."""
    suffixes = tuple(item.lower() for item in string_list(config, "archive_suffixes"))
    allowed = set(string_list(config, "archive_allowlist"))
    paths = (path.relative_to(repo).as_posix() for path in tracked_files(repo))
    return sorted(path for path in paths if path.lower().endswith(suffixes) and path not in allowed)


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=repository_root(__file__))
    parser.add_argument("--config", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the tracked-archive check."""
    args = build_parser().parse_args(argv)
    try:
        archives = unexpected_archives(args.repo, load_config(args.repo, args.config))
    except QualityError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    if archives:
        print(f"FAIL: {len(archives)} unexpected tracked archive(s)")
        for path in archives:
            print(f"  {path}")
        return 1
    print("OK: no unexpected archives are tracked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
