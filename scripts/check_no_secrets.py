"""Detect common tracked secret files and high-confidence credential patterns."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path, PurePosixPath

from quality_common import QualityError, load_config, repository_root, string_list, tracked_files

_PATTERNS = (
    ("private key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("AWS access key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b")),
    ("prefixed API token", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b")),
    ("Slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b")),
    (
        "embedded credential",
        re.compile(
            r"(?i)\b(?:api[_-]?key|secret[_-]?key|access[_-]?token|password)\b"
            r"\s*[:=]\s*[\"'](?!example|dummy|replace|changeme|test)"
            r"[A-Za-z0-9+/=_-]{20,}[\"']"
        ),
    ),
)


def _matches_glob(relative: str, patterns: list[str]) -> bool:
    path = PurePosixPath(relative)
    return any(path.match(pattern) for pattern in patterns)


def scan_repository(repo: Path, config: dict[str, object]) -> list[str]:
    """Return safe, redacted findings for tracked repository files."""
    allowed = set(string_list(config, "secret_allowed_paths"))
    banned_names = set(string_list(config, "secret_banned_names"))
    banned_globs = string_list(config, "secret_banned_globs")
    findings: list[str] = []
    for path in tracked_files(repo):
        relative = path.relative_to(repo).as_posix()
        if relative in allowed or not path.is_file():
            continue
        if path.name in banned_names or _matches_glob(relative, banned_globs):
            findings.append(f"tracked secret-like file: {relative}")
            continue
        if path.is_symlink():
            continue
        try:
            raw = path.read_bytes()
        except OSError as exc:
            findings.append(f"unreadable tracked file: {relative} ({exc})")
            continue
        if b"\0" in raw:
            continue
        for line_number, line in enumerate(raw.decode("utf-8", errors="ignore").splitlines(), 1):
            for label, pattern in _PATTERNS:
                if pattern.search(line):
                    findings.append(f"{label}: {relative}:{line_number}")
    return findings


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=repository_root(__file__))
    parser.add_argument("--config", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the tracked-secret check."""
    args = build_parser().parse_args(argv)
    try:
        findings = scan_repository(args.repo, load_config(args.repo, args.config))
    except QualityError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    if findings:
        print(f"FAIL: {len(findings)} potential secret issue(s)")
        for finding in findings:
            print(f"  {finding}")
        return 1
    print("OK: no tracked secret files or high-confidence credential patterns found")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
