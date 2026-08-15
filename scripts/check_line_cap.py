"""Enforce a configurable line-count limit for source files."""

from __future__ import annotations

import argparse
import sys
import tokenize
from pathlib import Path

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

_TOKEN_SKIP = {
    tokenize.ENCODING,
    tokenize.ENDMARKER,
    tokenize.NEWLINE,
    tokenize.NL,
    tokenize.INDENT,
    tokenize.DEDENT,
    tokenize.COMMENT,
}


def raw_line_count(path: Path) -> int:
    """Count physical lines."""
    return len(path.read_text(encoding="utf-8").splitlines())


def logical_line_count(path: Path) -> int:
    """Count non-blank, non-comment lines."""
    if path.suffix.lower() != ".py":
        lines = path.read_text(encoding="utf-8").splitlines()
        return sum(bool(line.strip()) and not line.lstrip().startswith(("#", "//")) for line in lines)
    source_lines: set[int] = set()
    with path.open("rb") as handle:
        for token in tokenize.tokenize(handle.readline):
            if token.type not in _TOKEN_SKIP:
                source_lines.update(range(token.start[0], token.end[0] + 1))
    return len(source_lines)


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


def find_violations(files: list[Path], limit: int, mode: str) -> list[tuple[Path, int]]:
    """Return every file whose selected line count exceeds the limit."""
    measure = raw_line_count if mode == "raw" else logical_line_count
    return [(path, count) for path in files if (count := measure(path)) > limit]


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
        violations = find_violations(files, limit, mode)
    except (IndentationError, OSError, QualityError, SyntaxError, tokenize.TokenError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    if violations:
        print(f"FAIL: {len(violations)} file(s) exceed {limit} {mode} lines")
        for path, count in violations:
            print(f"  {path.relative_to(args.repo)}: {count}")
        return 1
    print(f"OK: {len(files)} file(s) are within {limit} {mode} lines")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
