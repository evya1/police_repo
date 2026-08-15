"""Require explicit, least-privilege permissions in GitHub Actions workflows."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Mapping
from pathlib import Path

import yaml
from quality_common import QualityError, load_config, repository_root, safe_repo_path, string_list

_VALID_LEVELS = {"none", "read", "write"}


def permission_issues(label: str, value: object, allowed_writes: set[str]) -> list[str]:
    """Validate one workflow or job permissions declaration."""
    if not isinstance(value, Mapping):
        return [f"{label}: permissions must be an explicit scope mapping"]
    issues: list[str] = []
    for raw_scope, raw_level in value.items():
        scope, level = str(raw_scope), str(raw_level).lower()
        if level not in _VALID_LEVELS:
            issues.append(f"{label}: invalid permission level {level!r} for {scope}")
        elif level == "write" and scope not in allowed_writes:
            issues.append(f"{label}: unapproved write permission for {scope}")
    return issues


def check_workflow(path: Path, allowed_writes: set[str]) -> list[str]:
    """Validate one workflow file."""
    try:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        return [f"{path.name}: cannot parse workflow ({exc})"]
    if not isinstance(document, Mapping):
        return [f"{path.name}: workflow must be a YAML mapping"]
    if "permissions" not in document:
        issues = [f"{path.name}: missing top-level permissions"]
    else:
        issues = permission_issues(path.name, document["permissions"], allowed_writes)
    jobs = document.get("jobs", {})
    if isinstance(jobs, Mapping):
        for job_name, job in jobs.items():
            if isinstance(job, Mapping) and "permissions" in job:
                label = f"{path.name} job {job_name}"
                issues.extend(permission_issues(label, job["permissions"], allowed_writes))
    return issues


def workflow_files(repo: Path, directories: list[str]) -> tuple[list[Path], list[str]]:
    """Collect configured workflow files and missing-directory issues."""
    files: set[Path] = set()
    issues: list[str] = []
    for relative in directories:
        directory = safe_repo_path(repo, relative)
        if not directory.is_dir():
            issues.append(f"workflow directory not found: {relative}")
            continue
        files.update(directory.glob("*.yml"))
        files.update(directory.glob("*.yaml"))
    return sorted(files), issues


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=repository_root(__file__))
    parser.add_argument("--config", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the workflow-permission check."""
    args = build_parser().parse_args(argv)
    try:
        config = load_config(args.repo, args.config)
        files, issues = workflow_files(args.repo, string_list(config, "workflow_dirs"))
        allowed = set(string_list(config, "workflow_allowed_write_permissions"))
        for path in files:
            issues.extend(check_workflow(path, allowed))
    except QualityError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    if issues:
        print(f"FAIL: {len(issues)} workflow permission issue(s)")
        for issue in issues:
            print(f"  {issue}")
        return 1
    print(f"OK: {len(files)} workflow file(s) use explicit minimal permissions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
