"""Verify that repository-local links in Markdown files resolve."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

from quality_common import (
    QualityError,
    is_excluded,
    load_config,
    repository_root,
    safe_repo_path,
    string_list,
)

_INLINE_LINK = re.compile(
    r"!?\[[^\]]*\]\(\s*(?:<([^>]+)>|([^\s)]+))"
    r"(?:\s+(?:\"[^\"]*\"|'[^']*'|\([^)]*\)))?\s*\)"
)
_REFERENCE_LINK = re.compile(r"^[ ]{0,3}\[[^\]]+\]:\s*(?:<([^>]+)>|(\S+))", re.MULTILINE)


def without_fenced_code(text: str) -> str:
    """Remove fenced code blocks before scanning Markdown syntax."""
    kept: list[str] = []
    fence: str | None = None
    for line in text.splitlines():
        stripped = line.lstrip()
        marker = stripped[:3]
        if marker in {"```", "~~~"}:
            fence = None if fence == marker else marker if fence is None else fence
            continue
        if fence is None:
            kept.append(line)
    return "\n".join(kept)


def extract_links(text: str) -> list[str]:
    """Extract inline destinations and reference-definition destinations."""
    clean = without_fenced_code(text)
    matches = list(_INLINE_LINK.finditer(clean)) + list(_REFERENCE_LINK.finditer(clean))
    return [next(group for group in match.groups() if group is not None) for match in matches]


def markdown_files(
    repo: Path, supplied_paths: list[Path], excluded_dirs: set[str]
) -> tuple[list[Path], list[str]]:
    """Collect Markdown files and missing-input errors."""
    found: set[Path] = set()
    errors: list[str] = []
    for supplied in supplied_paths:
        path = safe_repo_path(repo, supplied)
        if not path.exists():
            errors.append(f"Markdown path not found: {path.relative_to(repo)}")
            continue
        candidates = [path] if path.is_file() else path.rglob("*.md")
        found.update(
            candidate
            for candidate in candidates
            if candidate.is_file()
            and candidate.suffix.lower() == ".md"
            and not is_excluded(candidate, repo, excluded_dirs)
        )
    return sorted(found), errors


def resolve_local_link(repo: Path, document: Path, target: str) -> tuple[bool, str]:
    """Resolve one link and return validity plus an optional reason."""
    if target.startswith(("#", "//")) or urlsplit(target).scheme:
        return True, ""
    clean = unquote(target.split("#", 1)[0].split("?", 1)[0])
    if not clean:
        return True, ""
    candidate = repo / clean.lstrip("/") if clean.startswith("/") else document.parent / clean
    resolved = candidate.resolve()
    try:
        resolved.relative_to(repo.resolve())
    except ValueError:
        return False, "target escapes repository"
    return resolved.exists(), "target does not exist"


def broken_links(repo: Path, files: list[Path]) -> list[str]:
    """Return broken local-link reports."""
    issues: list[str] = []
    for document in files:
        text = document.read_text(encoding="utf-8")
        for target in extract_links(text):
            valid, reason = resolve_local_link(repo, document, target)
            if not valid:
                relative = document.relative_to(repo)
                issues.append(f"{relative} -> {target} ({reason})")
    return issues


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path)
    parser.add_argument("--repo", type=Path, default=repository_root(__file__))
    parser.add_argument("--config", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the Markdown local-link check."""
    args = build_parser().parse_args(argv)
    try:
        config = load_config(args.repo, args.config)
        supplied = args.paths or [Path(item) for item in string_list(config, "markdown_paths")]
        files, issues = markdown_files(
            args.repo, supplied, set(string_list(config, "exclude_dirs"))
        )
        issues.extend(broken_links(args.repo, files))
    except (OSError, UnicodeError, QualityError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    if issues:
        print(f"FAIL: {len(issues)} Markdown link issue(s)")
        for issue in issues:
            print(f"  {issue}")
        return 1
    print(f"OK: local links resolve in {len(files)} Markdown file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
