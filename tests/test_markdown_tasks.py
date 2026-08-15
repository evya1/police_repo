"""Tests for Markdown links and task-ledger sanity."""

from __future__ import annotations

import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import check_markdown_links  # noqa: E402
import check_task_ids  # noqa: E402

ID_PATTERN = re.compile(r"^T[0-9]{3,}$")


def make_valid_task_graph(root: Path) -> None:
    """Create one task and one matching TODO ledger row."""
    tasks = root / "docs/tasks"
    tasks.mkdir(parents=True)
    (tasks / "T001-create-boundary.md").write_text("# T001\n", encoding="utf-8")
    (root / "docs/TODO.md").write_text(
        "| ID | Status | Task |\n"
        "| --- | --- | --- |\n"
        "| T001 | ready | [Create boundary](tasks/T001-create-boundary.md) |\n",
        encoding="utf-8",
    )


def validate(root: Path) -> tuple[list[str], int, int]:
    """Validate the standard test task paths."""
    return check_task_ids.validate_task_graph(
        root, ["docs/TODO.md"], ["docs/tasks"], ID_PATTERN
    )


class MarkdownAndTaskTests(unittest.TestCase):
    """Exercise local-link resolution and task graph invariants."""

    def test_markdown_links_accept_local_external_and_fenced_examples(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            docs = root / "docs"
            docs.mkdir()
            (docs / "guide.md").write_text("# Guide\n", encoding="utf-8")
            readme = root / "README.md"
            readme.write_text(
                "[Guide](docs/guide.md)\n[Site](https://example.com)\n"
                "```markdown\n[Template](missing.md)\n```\n",
                encoding="utf-8",
            )
            self.assertEqual(check_markdown_links.broken_links(root, [readme]), [])

    def test_markdown_links_report_missing_and_escape(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            readme = root / "README.md"
            readme.write_text(
                "[Missing](none.md)\n[Escape](../outside.md)\n", encoding="utf-8"
            )
            issues = check_markdown_links.broken_links(root, [readme])
            self.assertEqual(len(issues), 2)
            self.assertIn("does not exist", issues[0])
            self.assertIn("escapes repository", issues[1])

    def test_markdown_files_report_missing_input(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            files, issues = check_markdown_links.markdown_files(
                root, [Path("missing")], set()
            )
            self.assertEqual(files, [])
            self.assertEqual(issues, ["Markdown path not found: missing"])

    def test_valid_task_graph(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_valid_task_graph(root)
            self.assertEqual(validate(root), ([], 1, 1))

    def test_duplicate_task_ids_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_valid_task_graph(root)
            duplicate_dir = root / "docs/tasks/nested"
            duplicate_dir.mkdir()
            (duplicate_dir / "T001-second-copy.md").write_text(
                "# duplicate\n", encoding="utf-8"
            )
            issues, _, _ = validate(root)
            self.assertTrue(any("duplicate task ID T001" in issue for issue in issues))

    def test_invalid_task_filename_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_valid_task_graph(root)
            (root / "docs/tasks/T002_Bad_Name.md").write_text("bad\n", encoding="utf-8")
            issues, _, _ = validate(root)
            self.assertTrue(any("invalid task filename" in issue for issue in issues))

    def test_todo_row_requires_matching_task_link(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_valid_task_graph(root)
            (root / "docs/TODO.md").write_text(
                "| ID | Task |\n| --- | --- |\n"
                "| T001 | [Wrong](tasks/T999-missing.md) |\n",
                encoding="utf-8",
            )
            issues, _, _ = validate(root)
            self.assertTrue(any("broken task link" in issue for issue in issues))
            self.assertTrue(any("does not link to its task file" in issue for issue in issues))

    def test_duplicate_todo_rows_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            make_valid_task_graph(root)
            todo = root / "docs/TODO.md"
            row = "| T001 | ready | [Create](tasks/T001-create-boundary.md) |\n"
            todo.write_text(
                "| ID | Status | Task |\n| --- | --- | --- |\n" + row + row,
                encoding="utf-8",
            )
            issues, _, _ = validate(root)
            self.assertTrue(any("duplicate TODO task ID T001" in issue for issue in issues))


if __name__ == "__main__":
    unittest.main()
