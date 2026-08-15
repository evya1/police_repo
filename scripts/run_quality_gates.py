"""Run the complete generic repository-gate suite."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from quality_common import repository_root, resolve_config

_CHECKS = (
    "check_line_cap.py",
    "check_no_secrets.py",
    "check_markdown_links.py",
    "check_docs_present.py",
    "check_task_ids.py",
    "check_source_archives.py",
    "check_workflow_permissions.py",
)


def run_checks(repo: Path, config: Path, python: str = sys.executable) -> list[str]:
    """Run every check and return the filenames of failed checks."""
    failed: list[str] = []
    for script_name in _CHECKS:
        print(f"Running {script_name}", flush=True)
        command = [
            python,
            str(repo / "scripts" / script_name),
            "--repo",
            str(repo),
            "--config",
            str(config),
        ]
        if subprocess.run(command, check=False).returncode != 0:
            failed.append(script_name)
    return failed


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=repository_root(__file__))
    parser.add_argument("--config", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run every configured generic repository gate."""
    args = build_parser().parse_args(argv)
    failed = run_checks(args.repo, resolve_config(args.repo, args.config))
    if failed:
        print(f"FAIL: {len(failed)} repository gate(s) failed: {', '.join(failed)}")
        return 1
    print(f"OK: all {len(_CHECKS)} generic repository gates passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
