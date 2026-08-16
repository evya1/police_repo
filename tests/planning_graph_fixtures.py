"""Shared scaffolding for planning-graph tests (parsing, checks, and CLI)."""

from __future__ import annotations

import textwrap
from pathlib import Path

CONFIG = textwrap.dedent(
    """
    task_dirs = ["docs/tasks"]
    todo_paths = ["docs/TODO.md"]
    component_ids = ["C01", "C02"]
    input_gate_ids = ["G-LIVE"]
    requirement_register = "docs/spec/CANONICAL_REQUIREMENTS.md"
    open_register = "docs/spec/OPEN_QUESTIONS.md"
    input_register = "docs/inputs/INPUT_REGISTER.md"
    """
).strip()

REQUIREMENTS = "| ID | Level |\n|---|---|\n| GAME-001 | MUST |\n| GAME-002 | MUST |\n"
OPEN = "| OPEN-001 | ... |\n| PLANQ-001 | ... |\n"
INPUTS = "| INPUT-001 | ... |\n"
TRACE_OK = "| Canonical ID | Primary component |\n|---|---|\n| GAME-001 | C01 |\n| GAME-002 | C01 |\n"


def write(root: Path, relative: str, text: str) -> None:
    """Write a file, creating parent directories as needed."""
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def scaffold(root: Path) -> None:
    """Populate the minimum register set the validator reads."""
    write(root, "config/repo_quality.toml", CONFIG)
    write(root, "docs/spec/CANONICAL_REQUIREMENTS.md", REQUIREMENTS)
    write(root, "docs/spec/OPEN_QUESTIONS.md", OPEN)
    write(root, "docs/inputs/INPUT_REGISTER.md", INPUTS)
    write(root, "docs/spec/TRACEABILITY.md", TRACE_OK)
    write(root, "docs/components/C01/PRD.md", "# C01\n")


def task_text(
    task_id: str,
    *,
    component: str = "C01",
    gates: str = "gates: []\n",
    deps: str = "depends_on: []\n",
    status: str = "blocked",
    implementation_state: str = "not_started",
) -> str:
    """Render one synthetic task file's full text."""
    lines = [
        "---",
        f"id: {task_id}",
        f"status: {status}",
        f"implementation_state: {implementation_state}",
        "priority: P0",
        "task_type: component",
        f"component: {component}",
        "optional: false",
        "implements:",
        "  - GAME-001",
        "context_files:",
        "  - docs/components/C01/PRD.md",
        "read_set: []",
        deps.rstrip("\n"),
        gates.rstrip("\n"),
        "parallel_safe: true",
        "claimed_by:",
        "claim_expires_at:",
        "write_set:",
        f"  - src/example/{task_id.lower()}.py",
        "risk: low",
        "---",
        "",
        f"# {task_id}",
        "",
        "## Acceptance criteria",
        "",
        "- [ ] Something measurable. `{#anchor_a}`",
        "",
    ]
    return "\n".join(lines)
