"""Command-level tests for the planning-graph validator entry point."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

import check_planning_graph  # noqa: E402
from helpers import captured_main  # noqa: E402
from planning_graph_fixtures import scaffold, task_text, write  # noqa: E402


class PlanningGraphCliTests(unittest.TestCase):
    """Exercise the command-line entry point end to end."""

    def test_main_success(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            scaffold(root)
            write(root, "docs/tasks/T001-a.md", task_text("T001", status="ready"))
            write(root, "docs/tasks/T002-b.md", task_text("T002", deps="depends_on:\n  - T001\n"))
            code, output = captured_main(check_planning_graph.main, ["--repo", str(root)])
            self.assertEqual(code, 0, output)
            self.assertIn("OK:", output)

    def test_main_reports_unknown_component_and_missing_context_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            scaffold(root)
            write(root, "docs/tasks/T001-a.md", task_text("T001", component="C99"))
            code, output = captured_main(check_planning_graph.main, ["--repo", str(root)])
            self.assertEqual(code, 1)
            self.assertIn("unknown component", output)

    def test_main_reports_unresolved_gate_and_missing_anchor(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            scaffold(root)
            gates = "gates:\n  - id: OPEN-999\n    kind: open\n    scope: nope\n    blocks: criterion\n"
            write(root, "docs/tasks/T001-a.md", task_text("T001", gates=gates))
            code, output = captured_main(check_planning_graph.main, ["--repo", str(root)])
            self.assertEqual(code, 1)
            self.assertIn("does not resolve", output)
            self.assertIn("no matching acceptance-criterion anchor", output)

    def test_main_reports_read_write_overlap(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            scaffold(root)
            text = task_text("T001").replace("read_set: []", "read_set:\n  - src/example/t001.py")
            write(root, "docs/tasks/T001-a.md", text)
            code, output = captured_main(check_planning_graph.main, ["--repo", str(root)])
            self.assertEqual(code, 1)
            self.assertIn("read_set overlaps write_set", output)

    def test_main_fails_cleanly_on_missing_config(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            code, output = captured_main(check_planning_graph.main, ["--repo", directory])
            self.assertEqual(code, 1)
            self.assertIn("FAIL", output)


if __name__ == "__main__":
    unittest.main()
