"""Tests for planning-graph parsing helpers and graph-level checks."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

import planning_graph_checks as checks  # noqa: E402
import planning_graph_common as common  # noqa: E402
from planning_graph_fixtures import scaffold, task_text, write  # noqa: E402


class PlanningGraphParsingTests(unittest.TestCase):
    """Exercise the frontmatter/register parsers directly."""

    def test_parse_task_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            scaffold(root)
            write(root, "docs/tasks/T001-a.md", task_text("T001"))
            task = common.parse_task(root / "docs/tasks/T001-a.md")
            self.assertEqual(task.component, "C01")
            self.assertEqual(task.implements, ["GAME-001"])
            self.assertIn("anchor_a", task.anchors)

    def test_parse_task_missing_frontmatter_raises(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.md"
            path.write_text("no frontmatter here", encoding="utf-8")
            with self.assertRaises(ValueError):
                common.parse_task(path)

    def test_register_loaders(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            scaffold(root)
            self.assertEqual(
                common.load_requirement_ids(root, "docs/spec/CANONICAL_REQUIREMENTS.md"),
                {"GAME-001", "GAME-002"},
            )
            self.assertIn("OPEN-001", common.load_open_ids(root, "docs/spec/OPEN_QUESTIONS.md"))
            self.assertIn("INPUT-001", common.load_input_ids(root, "docs/inputs/INPUT_REGISTER.md"))


class GraphCheckTests(unittest.TestCase):
    """Exercise the graph-level checks directly."""

    def test_write_set_overlap_flagged_only_for_concurrent_candidates(self) -> None:
        a = common.Task("A", Path(), {"write_set": ["x"], "depends_on": []}, "")
        b = common.Task("B", Path(), {"write_set": ["x"], "depends_on": []}, "")
        c = common.Task("C", Path(), {"write_set": ["x"], "depends_on": ["A"]}, "")
        issues = common.Issues()
        checks.check_write_set_overlap([a, b, c], issues)
        joined = "\n".join(issues.items)
        self.assertIn("A and B", joined)
        self.assertNotIn("A and C", joined)

    def test_dependency_graph_flags_dangling_and_cycle(self) -> None:
        a = common.Task("A", Path(), {"depends_on": ["B"]}, "")
        b = common.Task("B", Path(), {"depends_on": ["A"]}, "")
        c = common.Task("C", Path(), {"depends_on": ["ZZZ"]}, "")
        issues = common.Issues()
        checks.check_dependency_graph([a, b, c], issues)
        joined = "\n".join(issues.items)
        self.assertIn("dangling depends_on", joined)
        self.assertIn("cycle", joined)

    def test_readiness_flags_ready_task_with_start_gate(self) -> None:
        # Reproduces the exact T002 contradiction: status ready but a
        # blocks:start gate — readiness requires no such gate.
        start_gate = {"id": "PLANQ-002", "kind": "decision", "scope": "x", "blocks": "start"}
        task = common.Task("T002", Path(), {"status": "ready", "depends_on": [], "gates": [start_gate]}, "")
        issues = common.Issues()
        checks.check_readiness_consistency([task], issues)
        self.assertTrue(any("blocks: start" in item for item in issues.items))

    def test_readiness_flags_blocked_task_with_no_mechanical_reason(self) -> None:
        # Reproduces the exact T001 contradiction: status blocked with an
        # empty depends_on and no gates.
        task = common.Task("T001", Path(), {"status": "blocked", "depends_on": [], "gates": []}, "")
        issues = common.Issues()
        checks.check_readiness_consistency([task], issues)
        self.assertTrue(any("no unfinished depends_on and no blocks:start gate" in item for item in issues.items))

    def test_readiness_accepts_consistent_ready_and_blocked_tasks(self) -> None:
        criterion_gate = {"id": "OPEN-001", "kind": "open", "scope": "x", "blocks": "criterion"}
        start_gate = {"id": "PLANQ-002", "kind": "decision", "scope": "x", "blocks": "start"}
        ready_with_criterion_gate = common.Task("A", Path(), {"status": "ready", "depends_on": [], "gates": [criterion_gate]}, "")
        blocked_by_gate = common.Task("B", Path(), {"status": "blocked", "depends_on": [], "gates": [start_gate]}, "")
        done_dep = common.Task("C", Path(), {"status": "done", "depends_on": [], "gates": []}, "")
        blocked_by_dep = common.Task("D", Path(), {"status": "blocked", "depends_on": ["E"], "gates": []}, "")
        unfinished_dep = common.Task("E", Path(), {"status": "blocked", "depends_on": [], "gates": [start_gate]}, "")
        issues = common.Issues()
        checks.check_readiness_consistency(
            [ready_with_criterion_gate, blocked_by_gate, done_dep, blocked_by_dep, unfinished_dep], issues
        )
        self.assertEqual(issues.items, [])

    def test_todo_consistency_flags_mismatched_row(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write(
                root,
                "docs/TODO.md",
                "| ID | Component | Type | Status |\n|---|---|---|---|\n| T001 | C01 | component | blocked |\n",
            )
            task = common.Task("T001", Path(), {"status": "ready", "component": "C01", "task_type": "component"}, "")
            issues = common.Issues()
            checks.check_todo_consistency([task], root, ["docs/TODO.md"], issues)
            self.assertTrue(any("status" in item and "disagrees" in item for item in issues.items))

    def test_todo_consistency_accepts_matching_row(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write(
                root,
                "docs/TODO.md",
                "| ID | Component | Type | Status |\n|---|---|---|---|\n| T001 | C01 | component | ready |\n",
            )
            task = common.Task("T001", Path(), {"status": "ready", "component": "C01", "task_type": "component"}, "")
            issues = common.Issues()
            checks.check_todo_consistency([task], root, ["docs/TODO.md"], issues)
            self.assertEqual(issues.items, [])

    def test_requirement_ownership_flags_conflict_and_missing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write(
                root,
                "docs/spec/TRACEABILITY.md",
                "| Canonical ID | Primary component |\n|---|---|\n| GAME-001 | C01 |\n| GAME-001 | C02 |\n",
            )
            issues = common.Issues()
            checks.check_requirement_ownership(root, {"GAME-001", "GAME-002"}, {"C01", "C02"}, issues)
            joined = "\n".join(issues.items)
            self.assertIn("conflicting primary owners", joined)
            self.assertIn("no primary component", joined)


if __name__ == "__main__":
    unittest.main()
