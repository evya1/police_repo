"""Tests for workflow permissions and the unified gate runner."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import check_workflow_permissions  # noqa: E402
import run_quality_gates  # noqa: E402


def write_workflow(root: Path, content: str) -> Path:
    """Write one workflow under the conventional directory."""
    directory = root / ".github/workflows"
    directory.mkdir(parents=True)
    path = directory / "ci.yml"
    path.write_text(content, encoding="utf-8")
    return path


class WorkflowAndRunnerTests(unittest.TestCase):
    """Exercise permission policy and check orchestration."""

    def test_minimal_workflow_permissions_pass(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = write_workflow(
                Path(directory),
                "permissions:\n  contents: read\njobs:\n  verify:\n    runs-on: ubuntu-latest\n",
            )
            self.assertEqual(check_workflow_permissions.check_workflow(path, set()), [])

    def test_missing_permissions_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = write_workflow(Path(directory), "jobs: {}\n")
            self.assertEqual(
                check_workflow_permissions.check_workflow(path, set()),
                ["ci.yml: missing top-level permissions"],
            )

    def test_unapproved_job_write_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = write_workflow(
                Path(directory),
                "permissions:\n  contents: read\njobs:\n  deploy:\n"
                "    permissions:\n      id-token: write\n",
            )
            issues = check_workflow_permissions.check_workflow(path, set())
            self.assertEqual(
                issues, ["ci.yml job deploy: unapproved write permission for id-token"]
            )
            self.assertEqual(check_workflow_permissions.check_workflow(path, {"id-token"}), [])

    def test_broad_string_permissions_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = write_workflow(Path(directory), "permissions: write-all\njobs: {}\n")
            issues = check_workflow_permissions.check_workflow(path, set())
            self.assertIn("explicit scope mapping", issues[0])

    def test_workflow_files_accept_yml_and_yaml(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workflow_dir = root / ".github/workflows"
            workflow_dir.mkdir(parents=True)
            (workflow_dir / "a.yml").write_text("permissions: {}\n", encoding="utf-8")
            (workflow_dir / "b.yaml").write_text("permissions: {}\n", encoding="utf-8")
            files, issues = check_workflow_permissions.workflow_files(root, [".github/workflows"])
            self.assertEqual(len(files), 2)
            self.assertEqual(issues, [])

    def test_runner_executes_every_gate_and_collects_failures(self) -> None:
        calls: list[list[str]] = []

        def fake_run(command: list[str], check: bool) -> SimpleNamespace:
            self.assertFalse(check)
            calls.append(command)
            return SimpleNamespace(returncode=int("check_task_ids.py" in command[1]))

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with mock.patch.object(run_quality_gates.subprocess, "run", fake_run):
                failed = run_quality_gates.run_checks(root, root / "quality.toml", "python")
        self.assertEqual(failed, ["check_task_ids.py"])
        self.assertEqual(len(calls), len(run_quality_gates._CHECKS))
        self.assertTrue(all("--repo" in command and "--config" in command for command in calls))


if __name__ == "__main__":
    unittest.main()
