"""Command-level tests for content and planning gates."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

import check_docs_present  # noqa: E402
import check_markdown_links  # noqa: E402
import check_task_ids  # noqa: E402
import check_workflow_permissions  # noqa: E402
from helpers import captured_main  # noqa: E402


class ContentGateCliTests(unittest.TestCase):
    """Exercise success and failure reporting through public CLIs."""

    def test_document_main_success_and_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "quality.toml"
            config.write_text('required_docs = ["README.md"]\n', encoding="utf-8")
            readme = root / "README.md"
            readme.write_text("ready\n", encoding="utf-8")
            arguments = ["--repo", str(root), "--config", str(config)]
            self.assertEqual(captured_main(check_docs_present.main, arguments)[0], 0)
            readme.unlink()
            result, output = captured_main(check_docs_present.main, arguments)
            self.assertEqual(result, 1)
            self.assertIn("README.md", output)

    def test_markdown_main_success_and_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "quality.toml"
            config.write_text(
                'markdown_paths = ["README.md"]\nexclude_dirs = []\n', encoding="utf-8"
            )
            readme = root / "README.md"
            readme.write_text("[Self](README.md)\n", encoding="utf-8")
            arguments = ["--repo", str(root), "--config", str(config)]
            self.assertEqual(captured_main(check_markdown_links.main, arguments)[0], 0)
            readme.write_text("[Broken](missing.md)\n", encoding="utf-8")
            self.assertEqual(captured_main(check_markdown_links.main, arguments)[0], 1)

    def test_task_main_skip_success_and_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "quality.toml"
            config.write_text(
                'todo_paths = []\ntask_dirs = []\ntask_id_pattern = "^T[0-9]{3,}$"\n',
                encoding="utf-8",
            )
            arguments = ["--repo", str(root), "--config", str(config)]
            self.assertEqual(captured_main(check_task_ids.main, arguments)[0], 0)
            tasks = root / "docs/tasks"
            tasks.mkdir(parents=True)
            task = tasks / "T001-do-work.md"
            task.write_text("# T001\n", encoding="utf-8")
            (root / "docs/TODO.md").write_text(
                "| ID | Task |\n| --- | --- |\n| T001 | [Do](tasks/T001-do-work.md) |\n",
                encoding="utf-8",
            )
            config.write_text(
                'todo_paths = ["docs/TODO.md"]\ntask_dirs = ["docs/tasks"]\n'
                'task_id_pattern = "^T[0-9]{3,}$"\n',
                encoding="utf-8",
            )
            self.assertEqual(captured_main(check_task_ids.main, arguments)[0], 0)
            task.unlink()
            self.assertEqual(captured_main(check_task_ids.main, arguments)[0], 1)

    def test_workflow_main_success_and_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workflows = root / ".github/workflows"
            workflows.mkdir(parents=True)
            workflow = workflows / "ci.yml"
            workflow.write_text("permissions:\n  contents: read\njobs: {}\n", encoding="utf-8")
            config = root / "quality.toml"
            config.write_text(
                'workflow_dirs = [".github/workflows"]\nworkflow_allowed_write_permissions = []\n',
                encoding="utf-8",
            )
            arguments = ["--repo", str(root), "--config", str(config)]
            self.assertEqual(captured_main(check_workflow_permissions.main, arguments)[0], 0)
            workflow.write_text("permissions:\n  contents: write\njobs: {}\n", encoding="utf-8")
            self.assertEqual(captured_main(check_workflow_permissions.main, arguments)[0], 1)


if __name__ == "__main__":
    unittest.main()
