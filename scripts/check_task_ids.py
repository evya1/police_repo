"""Validate task filenames, unique IDs, and TODO links to task files."""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import unquote, urlsplit

from quality_common import (
    QualityError,
    load_config,
    repository_root,
    safe_repo_path,
    string_list,
    string_value,
)

_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_LINK = re.compile(r"\[[^\]]*\]\(\s*(?:<([^>]+)>|([^\s)]+))")


def task_file_id(path: Path, id_pattern: re.Pattern[str]) -> str | None:
    """Return the task ID when a filename follows ``ID-kebab-title.md``."""
    task_id, separator, slug = path.stem.partition("-")
    if separator and id_pattern.fullmatch(task_id) and _SLUG.fullmatch(slug):
        return task_id
    return None


def links_in(text: str) -> list[str]:
    """Extract simple Markdown inline-link destinations."""
    return [
        next(group for group in match.groups() if group is not None)
        for match in _LINK.finditer(text)
    ]


def resolve_link(repo: Path, todo: Path, target: str) -> Path | None:
    """Resolve a local TODO link, returning ``None`` for external links."""
    if target.startswith(("#", "//")) or urlsplit(target).scheme:
        return None
    clean = unquote(target.split("#", 1)[0].split("?", 1)[0])
    candidate = repo / clean.lstrip("/") if clean.startswith("/") else todo.parent / clean
    return candidate.resolve()


def todo_rows(text: str, id_pattern: re.Pattern[str]) -> list[tuple[str, str]]:
    """Return task IDs and source rows from a Markdown table."""
    rows: list[tuple[str, str]] = []
    for line in text.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = line.strip().strip("|").split("|")
        candidate = cells[0].strip().strip("`") if cells else ""
        if id_pattern.fullmatch(candidate):
            rows.append((candidate, line))
    return rows


def validate_task_graph(
    repo: Path,
    todo_paths: list[str],
    task_dirs: list[str],
    id_pattern: re.Pattern[str],
) -> tuple[list[str], int, int]:
    """Return issues plus counts of valid task files and TODO rows."""
    issues: list[str] = []
    task_files: list[Path] = []
    for relative in task_dirs:
        directory = safe_repo_path(repo, relative)
        if not directory.is_dir():
            issues.append(f"task directory not found: {relative}")
        else:
            task_files.extend(directory.rglob("*.md"))
    by_id: dict[str, list[Path]] = defaultdict(list)
    for path in sorted(task_files):
        task_id = task_file_id(path, id_pattern)
        if task_id is None:
            issues.append(f"invalid task filename: {path.relative_to(repo)}")
        else:
            by_id[task_id].append(path.resolve())
    for task_id, paths in sorted(by_id.items()):
        if len(paths) > 1:
            rendered = ", ".join(str(path.relative_to(repo)) for path in paths)
            issues.append(f"duplicate task ID {task_id}: {rendered}")

    rows: list[tuple[str, Path, str]] = []
    for relative in todo_paths:
        todo = safe_repo_path(repo, relative)
        if not todo.is_file():
            issues.append(f"TODO file not found: {relative}")
            continue
        text = todo.read_text(encoding="utf-8")
        rows.extend((task_id, todo, row) for task_id, row in todo_rows(text, id_pattern))
        for target in links_in(text):
            resolved = resolve_link(repo, todo, target)
            task_id = resolved.stem.partition("-")[0] if resolved is not None else ""
            if resolved is not None and id_pattern.fullmatch(task_id) and not resolved.is_file():
                issues.append(f"broken task link: {todo.relative_to(repo)} -> {target}")
    counts = Counter(task_id for task_id, _, _ in rows)
    for task_id, count in sorted(counts.items()):
        if count > 1:
            issues.append(f"duplicate TODO task ID {task_id}: {count} rows")
    for task_id, todo, row in rows:
        resolved = {resolve_link(repo, todo, target) for target in links_in(row)}
        expected = set(by_id.get(task_id, []))
        if not expected or expected.isdisjoint(resolved):
            msg = f"TODO row {task_id} does not link to its task file in {todo.relative_to(repo)}"
            issues.append(msg)
    return issues, sum(len(paths) for paths in by_id.values()), len(rows)


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=repository_root(__file__))
    parser.add_argument("--config", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run task-graph validation."""
    args = build_parser().parse_args(argv)
    try:
        config = load_config(args.repo, args.config)
        todo_paths = string_list(config, "todo_paths")
        task_dirs = string_list(config, "task_dirs")
        if not todo_paths and not task_dirs:
            print("SKIP: task graph paths are not configured")
            return 0
        pattern = re.compile(string_value(config, "task_id_pattern"))
        issues, task_count, row_count = validate_task_graph(
            args.repo, todo_paths, task_dirs, pattern
        )
    except (OSError, UnicodeError, QualityError, re.error) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    if issues:
        print(f"FAIL: {len(issues)} task-graph issue(s)")
        for issue in issues:
            print(f"  {issue}")
        return 1
    print(f"OK: {task_count} task file(s), {row_count} unique linked TODO row(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
