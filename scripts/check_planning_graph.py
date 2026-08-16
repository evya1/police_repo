"""Validate the bounded-context planning graph: components, context files,
requirement ownership, gates, and the task dependency DAG.

See ``docs/spec/PRD_PLAN_TODO_AGENT_WORKFLOW.md`` section 6a for the semantics
this script enforces, and ``planning_graph_common.py`` for parsing helpers.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from planning_graph_checks import (
    check_dependency_graph,
    check_readiness_consistency,
    check_requirement_ownership,
    check_todo_consistency,
    check_write_set_overlap,
)
from planning_graph_common import (
    Issues,
    Task,
    load_input_ids,
    load_open_ids,
    load_requirement_ids,
    load_tasks,
)
from quality_common import QualityError, load_config, safe_repo_path, string_list

_TASK_TYPES = {"foundation", "component", "integration", "verification", "governance", "release"}
_GATE_KINDS = {"open", "input", "input_gate", "decision"}
_BLOCK_LEVELS = {"start", "criterion", "integration"}
# Evidence-based implementation state, independent of the claimability `status`.
_IMPL_STATES = {"not_started", "partial", "implementation_present", "review_pending", "complete"}


def check_component(task: Task, component_ids: set[str], issues: Issues) -> None:
    if task.component not in component_ids and task.component != "system":
        issues.add(f"{task.task_id}: unknown component {task.component!r}")
    if task.task_type not in _TASK_TYPES:
        issues.add(f"{task.task_id}: unknown task_type {task.task_type!r}")
    if task.implementation_state not in _IMPL_STATES:
        issues.add(f"{task.task_id}: unknown implementation_state {task.implementation_state!r}")
    if task.implementation_state == "complete" and task.status != "done":
        issues.add(f"{task.task_id}: implementation_state 'complete' requires status 'done'")
    if task.status == "done" and task.implementation_state != "complete":
        issues.add(f"{task.task_id}: status 'done' requires implementation_state 'complete'")


def check_context_files(task: Task, repo: Path, issues: Issues) -> None:
    for relative in task.context_files:
        if not safe_repo_path(repo, relative).is_file():
            issues.add(f"{task.task_id}: context_files entry does not exist: {relative}")


def check_implements(task: Task, requirement_ids: set[str], issues: Issues) -> None:
    for req in task.implements:
        if req not in requirement_ids:
            issues.add(f"{task.task_id}: implements unknown requirement {req!r}")


def check_gates(task: Task, open_ids: set[str], input_ids: set[str], gate_ids: set[str], issues: Issues) -> None:
    for gate in task.gates:
        kind, gate_id, blocks = gate.get("kind"), gate.get("id"), gate.get("blocks")
        if kind not in _GATE_KINDS:
            issues.add(f"{task.task_id}: gate has unknown kind {kind!r}")
        if blocks not in _BLOCK_LEVELS:
            issues.add(f"{task.task_id}: gate {gate_id!r} has unknown blocks level {blocks!r}")
        register = {"open": open_ids, "input": input_ids, "input_gate": gate_ids, "decision": open_ids}.get(kind, set())
        if gate_id not in register:
            issues.add(f"{task.task_id}: gate id {gate_id!r} does not resolve for kind {kind!r}")
        scope = gate.get("scope")
        if scope and blocks in {"criterion", "start"} and f"{{#{scope}}}" not in task.body and blocks == "criterion":
            issues.add(f"{task.task_id}: gate scope {scope!r} has no matching acceptance-criterion anchor")


def check_read_write_disjoint(task: Task, issues: Issues) -> None:
    overlap = set(task.read_set) & set(task.write_set)
    if overlap:
        issues.add(f"{task.task_id}: read_set overlaps write_set (already implicitly readable): {sorted(overlap)}")


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--config", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run every planning-graph check and report results."""
    args = build_parser().parse_args(argv)
    repo = args.repo
    try:
        config = load_config(repo, args.config)
        task_dirs = string_list(config, "task_dirs")
        todo_paths = string_list(config, "todo_paths")
        component_ids = set(string_list(config, "component_ids"))
        gate_ids = set(string_list(config, "input_gate_ids"))
        requirement_ids = load_requirement_ids(repo, config["requirement_register"])
        open_ids = load_open_ids(repo, config["open_register"]) | gate_ids
        input_ids = load_input_ids(repo, config["input_register"])
        tasks = load_tasks(repo, task_dirs)
    except (QualityError, OSError, ValueError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    issues = Issues()
    for task in tasks:
        check_component(task, component_ids, issues)
        check_context_files(task, repo, issues)
        check_implements(task, requirement_ids, issues)
        check_gates(task, open_ids, input_ids, gate_ids, issues)
        check_read_write_disjoint(task, issues)
    check_write_set_overlap(tasks, issues)
    check_dependency_graph(tasks, issues)
    check_readiness_consistency(tasks, issues)
    check_todo_consistency(tasks, repo, todo_paths, issues)
    check_requirement_ownership(repo, requirement_ids, component_ids, issues)

    if issues.items:
        print(f"FAIL: {len(issues.items)} planning-graph issue(s)")
        for item in issues.items:
            print(f"  {item}")
        return 1
    print(f"OK: {len(tasks)} task(s), {len(component_ids)} component(s), 0 issues")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
