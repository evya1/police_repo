"""Line counting and the T040 per-file baseline ratchet, split out of `check_line_cap.py`
to keep the CLI entrypoint under the repository's own line cap.
"""

from __future__ import annotations

import tokenize
from pathlib import Path

from quality_common import QualityError

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


def _is_source_line(line: str) -> bool:
    """Return True if a line is non-blank and not a comment."""
    stripped = line.strip()
    return bool(stripped) and not stripped.startswith(("#", "//"))


def logical_line_count(path: Path) -> int:
    """Count non-blank, non-comment lines."""
    if path.suffix.lower() != ".py":
        lines = path.read_text(encoding="utf-8").splitlines()
        return sum(1 for line in lines if _is_source_line(line))
    source_lines: set[int] = set()
    with path.open("rb") as handle:
        for token in tokenize.tokenize(handle.readline):
            if token.type not in _TOKEN_SKIP:
                source_lines.update(range(token.start[0], token.end[0] + 1))
    return len(source_lines)


def find_violations(files: list[Path], limit: int, mode: str) -> list[tuple[Path, int]]:
    """Return every file whose selected line count exceeds the limit (baseline-unaware)."""
    measure = raw_line_count if mode == "raw" else logical_line_count
    return [(path, count) for path in files if (count := measure(path)) > limit]


def load_baseline(config: dict) -> dict[str, int]:
    """Read `[line_cap_baseline]`: exact repo-relative path -> pinned logical line count."""
    raw = config.get("line_cap_baseline", {})
    if not isinstance(raw, dict):
        raise QualityError("line_cap_baseline must be a TOML table of path -> integer")
    baseline: dict[str, int] = {}
    for key, value in raw.items():
        if not isinstance(value, int) or isinstance(value, bool):
            raise QualityError(f"line_cap_baseline[{key!r}] must be an integer line count")
        baseline[key] = value
    return baseline


def ratchet_problems(
    files: list[Path], repo: Path, limit: int, mode: str, baseline: dict[str, int]
) -> list[str]:
    """Reconcile measured counts against the pinned baseline; empty means the gate is clean.

    A file over `limit` needs an exact baseline entry matching its current count (missing
    or drifted-higher both fail; a genuine reduction must lower the baseline in the same
    commit). A file at or under `limit` must have no baseline entry. A baseline entry that
    names a path outside the scanned set (missing, wildcard, or directory-wide) fails too.
    """
    measure = raw_line_count if mode == "raw" else logical_line_count
    counts = {path.relative_to(repo).as_posix(): measure(path) for path in files}
    problems = []
    for rel, count in sorted(counts.items()):
        pinned = baseline.get(rel)
        if count > limit and pinned is None:
            problems.append(f"new unlisted violation: {rel} is {count} lines (limit {limit})")
        elif count > limit and pinned != count:
            problems.append(f"baseline drift: {rel} is {count} lines but baseline says {pinned}")
        elif count <= limit and pinned is not None:
            problems.append(f"stale baseline entry: {rel} is {count} lines (<= {limit}); remove it")
    problems += [
        f"baseline entry not in the scanned set (missing, wildcard, or directory-wide): {rel}"
        for rel in baseline if rel not in counts
    ]
    return problems
