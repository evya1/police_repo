"""Flag historical and source-oriented wording in current project documentation.

Current documentation states what the system requires, what the project decided,
why a decision is useful, how it is verified, and what remains unresolved. It does
not narrate where an idea was seen, how the planning structure evolved, or defend
the repository's originality.

This gate is a review aid, not a licence to delete words. A hit means the sentence
needs rewriting into direct project language; a human still reads the result. Exact
protocol literals are masked before matching so an interoperability identifier is
never reported for the prose word inside it.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from quality_common import (
    QualityError,
    load_config,
    repository_root,
    safe_repo_path,
    string_list,
    tracked_files,
)


def _compiled(patterns: list[str]) -> list[re.Pattern[str]]:
    """Compile each configured pattern case-insensitively."""
    try:
        return [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
    except re.error as exc:
        raise QualityError(f"invalid doc_language_patterns entry: {exc}") from exc


def _under(path: Path, roots: list[Path]) -> bool:
    """Return whether ``path`` is one of, or inside, the configured roots."""
    return any(path == root or root in path.parents for root in roots)


_MASK = "<protocol-literal>"


def mask_literals(line: str, literals: list[str]) -> str:
    """Blank out exact protocol literals so their prose words are not matched."""
    for literal in literals:
        line = line.replace(literal, _MASK)
    return line


def scan_file(path: Path, patterns: list[re.Pattern[str]], literals: list[str]) -> list[tuple[int, str, str]]:
    """Return ``(line number, matched text, pattern)`` for one file."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return []
    findings: list[tuple[int, str, str]] = []
    for number, line in enumerate(text.splitlines(), start=1):
        masked = mask_literals(line, literals)
        for pattern in patterns:
            match = pattern.search(masked)
            if match:
                findings.append((number, match.group(0), pattern.pattern))
    return findings


def findings_for(repo: Path, config: dict[str, object]) -> list[str]:
    """Return one formatted finding per offending line in the configured scope."""
    roots = [safe_repo_path(repo, entry) for entry in string_list(config, "doc_language_paths")]
    allowed = {safe_repo_path(repo, entry) for entry in string_list(config, "doc_language_allowlist")}
    patterns = _compiled(string_list(config, "doc_language_patterns"))
    literals = string_list(config, "doc_language_allowed_literals")
    reported: list[str] = []
    for path in tracked_files(repo):
        if path in allowed or not _under(path, roots) or not path.is_file():
            continue
        relative = path.relative_to(repo).as_posix()
        for number, text, pattern in scan_file(path, patterns, literals):
            reported.append(f"{relative}:{number}: {text!r} matches /{pattern}/")
    return sorted(reported)


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=repository_root(__file__))
    parser.add_argument("--config", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the documentation-language check."""
    args = build_parser().parse_args(argv)
    try:
        reported = findings_for(args.repo, load_config(args.repo, args.config))
    except QualityError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    if reported:
        print(f"FAIL: {len(reported)} documentation-language finding(s)")
        for item in reported:
            print(f"  {item}")
        print("Rewrite each into direct project language; do not simply delete the word.")
        return 1
    print("OK: no historical or source-oriented wording found in project documentation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
