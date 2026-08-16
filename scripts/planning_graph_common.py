"""Parsing and check helpers for the bounded-context planning-graph validator.

Split from ``check_planning_graph.py`` to respect the 150-logical-line cap
(``QR-005``). Pure functions only; no I/O beyond reading paths handed to it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

_FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)
_ANCHOR = re.compile(r"\{#([a-z0-9_]+)\}")
_REQ_ID = re.compile(r"^[A-Z][A-Z0-9]+-[0-9]{3}$")


@dataclass
class Task:
    """One parsed task file."""

    task_id: str
    path: Path
    frontmatter: dict
    body: str

    @property
    def component(self) -> str | None:
        return self.frontmatter.get("component")

    @property
    def task_type(self) -> str | None:
        return self.frontmatter.get("task_type")

    @property
    def implements(self) -> list[str]:
        return list(self.frontmatter.get("implements") or [])

    @property
    def context_files(self) -> list[str]:
        return list(self.frontmatter.get("context_files") or [])

    @property
    def read_set(self) -> list[str]:
        return list(self.frontmatter.get("read_set") or [])

    @property
    def write_set(self) -> list[str]:
        return list(self.frontmatter.get("write_set") or [])

    @property
    def depends_on(self) -> list[str]:
        return list(self.frontmatter.get("depends_on") or [])

    @property
    def gates(self) -> list[dict]:
        return list(self.frontmatter.get("gates") or [])

    @property
    def status(self) -> str | None:
        return self.frontmatter.get("status")

    @property
    def implementation_state(self) -> str | None:
        return self.frontmatter.get("implementation_state")

    @property
    def anchors(self) -> set[str]:
        return set(_ANCHOR.findall(self.body))


@dataclass
class Issues:
    """Accumulated validator findings."""

    items: list[str] = field(default_factory=list)

    def add(self, message: str) -> None:
        self.items.append(message)


def parse_task(path: Path) -> Task:
    """Parse one task file's YAML frontmatter and body."""
    text = path.read_text(encoding="utf-8")
    match = _FRONTMATTER.match(text)
    if not match:
        raise ValueError(f"no frontmatter block: {path}")
    frontmatter = yaml.safe_load(match.group(1)) or {}
    return Task(task_id=frontmatter.get("id", path.stem), path=path, frontmatter=frontmatter, body=match.group(2))


def load_tasks(repo: Path, task_dirs: list[str]) -> list[Task]:
    """Load every task file under the configured task directories."""
    tasks: list[Task] = []
    for relative in task_dirs:
        directory = repo / relative
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("T*.md")):
            tasks.append(parse_task(path))
    return tasks


def load_requirement_ids(repo: Path, register: str) -> set[str]:
    """Extract requirement IDs from the canonical register's first table column."""
    text = (repo / register).read_text(encoding="utf-8")
    ids: set[str] = set()
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        cell = line.strip("|").split("|", 1)[0].strip().strip("`")
        if _REQ_ID.fullmatch(cell):
            ids.add(cell)
    return ids


def load_open_ids(repo: Path, register: str) -> set[str]:
    """Extract OPEN-*/PLANQ-* IDs referenced as table rows in the OPEN register."""
    text = (repo / register).read_text(encoding="utf-8")
    return set(re.findall(r"\b(?:OPEN|PLANQ)-[0-9]{3}\b", text))


def load_input_ids(repo: Path, register: str) -> set[str]:
    """Extract INPUT-* IDs from the input register."""
    text = (repo / register).read_text(encoding="utf-8")
    return set(re.findall(r"\bINPUT-[0-9]{3}\b", text))
