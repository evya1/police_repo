"""Graph-level planning checks: write-set overlap (wave-aware), dependency DAG
validity, and single-owner requirement traceability.

Split from ``planning_graph_common.py`` to respect the 150-logical-line cap
(``QR-005``).
"""

from __future__ import annotations

from pathlib import Path

from planning_graph_common import Issues, Task


def _transitive_deps(task_id: str, by_id: dict[str, Task], cache: dict[str, set[str]]) -> set[str]:
    """Return every task transitively required by ``task_id``, memoized."""
    if task_id in cache:
        return cache[task_id]
    cache[task_id] = set()  # cycle guard against re-entrant lookups
    result: set[str] = set()
    for dep in by_id.get(task_id, Task("", Path(), {}, "")).depends_on:
        result.add(dep)
        result |= _transitive_deps(dep, by_id, cache)
    cache[task_id] = result
    return result


def check_write_set_overlap(tasks: list[Task], issues: Issues) -> None:
    """Flag write_set overlap only between tasks that could genuinely run in the
    same wave — i.e. neither is a transitive dependency of the other. Two tasks
    linked by depends_on never execute concurrently, so a shared path between
    them (e.g. T003 depending on T002 and both touching pyproject.toml) is not
    a wave-parallelism conflict."""
    by_id = {t.task_id: t for t in tasks}
    by_writes = {t.task_id: set(t.write_set) for t in tasks}
    cache: dict[str, set[str]] = {}
    ids = sorted(by_writes)
    for i, a in enumerate(ids):
        deps_a = _transitive_deps(a, by_id, cache)
        for b in ids[i + 1 :]:
            deps_b = _transitive_deps(b, by_id, cache)
            if a in deps_b or b in deps_a:
                continue
            overlap = by_writes[a] & by_writes[b]
            if overlap:
                issues.add(f"write_set overlap between concurrent-candidate {a} and {b}: {sorted(overlap)}")


def check_dependency_graph(tasks: list[Task], issues: Issues) -> None:
    """Flag dangling depends_on IDs and dependency cycles."""
    by_id = {t.task_id: t for t in tasks}
    for task in tasks:
        for dep in task.depends_on:
            if dep not in by_id:
                issues.add(f"{task.task_id}: dangling depends_on {dep!r}")

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(task_id: str) -> None:
        if task_id in visited or task_id not in by_id:
            return
        if task_id in visiting:
            issues.add(f"dependency cycle detected involving {task_id}")
            return
        visiting.add(task_id)
        for dep in by_id[task_id].depends_on:
            visit(dep)
        visiting.discard(task_id)
        visited.add(task_id)

    for task in tasks:
        visit(task.task_id)


def check_readiness_consistency(tasks: list[Task], issues: Issues) -> None:
    """Enforce PRD_PLAN_TODO_AGENT_WORKFLOW.md section 6a exactly: a task is
    `ready` iff every depends_on task is `done` and no gate has blocks:start.
    A `blocked` task must have a mechanically identifiable reason (an
    unfinished dependency or a blocks:start gate). Criterion/integration
    gates are never readiness blockers and are intentionally not inspected
    here — only blocks:start participates in the ready/blocked computation."""
    by_id = {t.task_id: t for t in tasks}
    for task in tasks:
        deps_done = all(by_id[d].status == "done" for d in task.depends_on if d in by_id)
        has_start_gate = any(g.get("blocks") == "start" for g in task.gates)
        if task.status == "ready" and (not deps_done or has_start_gate):
            reason = "an unfinished depends_on task" if not deps_done else "a gates: entry with blocks: start"
            issues.add(f"{task.task_id}: status is 'ready' but {reason} contradicts readiness")
        if task.status == "blocked" and deps_done and not has_start_gate:
            issues.add(f"{task.task_id}: status is 'blocked' with no unfinished depends_on and no blocks:start gate")


def check_todo_consistency(tasks: list[Task], repo: Path, todo_paths: list[str], issues: Issues) -> None:
    """Verify each TODO.md row agrees with its task file on ID, status,
    component, and task type, using the current TODO column headers."""
    by_id = {t.task_id: t for t in tasks}
    for relative in todo_paths:
        todo = repo / relative
        if not todo.is_file():
            continue
        header: list[str] | None = None
        for line in todo.read_text(encoding="utf-8").splitlines():
            if not line.strip().startswith("|"):
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if header is None:
                header = [c.lower() for c in cells]
                continue
            if set(cells[0]) <= {"-"}:
                continue
            row = dict(zip(header, cells, strict=False))
            task_id = row.get("id", "")
            if task_id not in by_id:
                continue
            task = by_id[task_id]
            for field, actual in (("component", task.component), ("type", task.task_type), ("status", task.status)):
                if field in row and row[field] != str(actual):
                    issues.add(f"TODO row {task_id}: {field} {row[field]!r} disagrees with task file {actual!r}")


def check_requirement_ownership(repo: Path, requirement_ids: set[str], component_ids: set[str], issues: Issues) -> None:
    """Flag any requirement with zero or more than one primary-owning component."""
    traceability = repo / "docs" / "spec" / "TRACEABILITY.md"
    if not traceability.is_file():
        return
    text = traceability.read_text(encoding="utf-8")
    owners: dict[str, str] = {}
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip().strip("`") for c in line.strip("|").split("|")]
        if len(cells) < 2 or cells[0] not in requirement_ids:
            continue
        req_id, owner = cells[0], cells[1]
        if owner not in component_ids and owner != "system":
            issues.add(f"TRACEABILITY.md: {req_id} has unknown primary component {owner!r}")
        if req_id in owners and owners[req_id] != owner:
            issues.add(f"TRACEABILITY.md: {req_id} has conflicting primary owners")
        owners[req_id] = owner
    missing = requirement_ids - owners.keys()
    if missing:
        issues.add(f"TRACEABILITY.md: {len(missing)} requirement(s) have no primary component: {sorted(missing)[:5]}...")
