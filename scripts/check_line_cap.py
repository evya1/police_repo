"""Enforce a configurable line-count limit for source files, ratcheted against a pinned
per-file baseline (T040) so historical debt cannot hide behind an unscanned directory.
An exact ``# line-cap: disable`` Python comment explicitly opts its file out.
"""

from __future__ import annotations

import argparse
import sys
import tokenize
from pathlib import Path

from line_cap_ratchet import (
    LINE_CAP_DISABLE_MARKER,
    find_violations,
    line_cap_disabled,
    load_baseline,
    logical_line_count,
    ratchet_problems,
    raw_line_count,
)
from quality_common import (
    QualityError,
    integer_value,
    is_excluded,
    load_config,
    repository_root,
    safe_repo_path,
    string_list,
    string_value,
)

__all__ = [
    "LINE_CAP_DISABLE_MARKER", "find_violations", "line_cap_disabled", "load_baseline",
    "logical_line_count", "ratchet_problems", "raw_line_count",
]


def collect_files(
    repo: Path,
    paths: list[Path],
    extensions: set[str],
    excluded_dirs: set[str],
) -> list[Path]:
    """Collect matching source files from explicit files and directories."""
    files: set[Path] = set()
    for supplied in paths:
        path = safe_repo_path(repo, supplied)
        if not path.exists():
            raise QualityError(f"line-cap path not found: {path}")
        candidates = [path] if path.is_file() else path.rglob("*")
        files.update(
            candidate
            for candidate in candidates
            if candidate.is_file()
            and candidate.suffix.lower() in extensions
            and not is_excluded(candidate, repo, excluded_dirs)
        )
    return sorted(files)


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--mode", choices=("raw", "logical"))
    parser.add_argument("--extensions", nargs="+")
    parser.add_argument("--repo", type=Path, default=repository_root(__file__))
    parser.add_argument("--config", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the line-cap check."""
    args = build_parser().parse_args(argv)
    try:
        config = load_config(args.repo, args.config)
        paths = args.paths or [
            Path(item)
            for key in ("source_dirs", "test_dirs", "script_dirs")
            for item in string_list(config, key)
        ]
        if args.limit is not None and args.limit <= 0:
            raise QualityError("--limit must be a positive integer")
        limit = args.limit if args.limit is not None else integer_value(config, "line_limit")
        mode = args.mode or string_value(config, "line_mode")
        if mode not in {"raw", "logical"}:
            raise QualityError("line_mode must be 'raw' or 'logical'")
        extensions = {
            item.lower() for item in (args.extensions or string_list(config, "code_extensions"))
        }
        excluded = set(string_list(config, "exclude_dirs"))
        files = collect_files(args.repo, paths, extensions, excluded)
        if not files:
            raise QualityError("no matching source files found")
        baseline = load_baseline(config)
        problems = ratchet_problems(files, args.repo, limit, mode, baseline)
        disabled_paths = {
            path.relative_to(args.repo).as_posix() for path in files if line_cap_disabled(path)
        }
        active_baseline_count = sum(rel not in disabled_paths for rel in baseline)
    except (IndentationError, OSError, QualityError, SyntaxError, tokenize.TokenError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    if problems:
        print(f"FAIL: {len(problems)} line-cap ratchet issue(s)")
        for problem in problems:
            print(f"  {problem}")
        return 1
    print(
        f"OK: {len(files)} file(s) are within {limit} {mode} lines "
        f"({active_baseline_count} baselined, {len(disabled_paths)} line-cap disabled)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
