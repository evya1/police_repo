"""Verify that configured required documents exist."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from quality_common import QualityError, load_config, repository_root, safe_repo_path, string_list


def missing_documents(repo: Path, required: list[str]) -> list[str]:
    """Return repository-relative required paths that do not exist."""
    return [relative for relative in required if not safe_repo_path(repo, relative).exists()]


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=repository_root(__file__))
    parser.add_argument("--config", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the required-document check."""
    args = build_parser().parse_args(argv)
    try:
        required = string_list(load_config(args.repo, args.config), "required_docs")
    except QualityError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    missing = missing_documents(args.repo, required)
    if missing:
        print(f"FAIL: {len(missing)} required document(s) missing")
        for path in missing:
            print(f"  {path}")
        return 1
    print(f"OK: all {len(required)} required document(s) exist")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
