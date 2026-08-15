"""Shared configuration and Git helpers for repository quality gates."""

from __future__ import annotations

import os
import subprocess
import tomllib
from pathlib import Path

Config = dict[str, object]


class QualityError(RuntimeError):
    """Raised when gate configuration or repository state is invalid."""


def repository_root(script_file: str) -> Path:
    """Return the repository root for a script stored in ``scripts/``."""
    return Path(script_file).resolve().parent.parent


def resolve_config(repo: Path, config_path: Path | None) -> Path:
    """Resolve an optional configuration path against the repository root."""
    path = config_path or Path("config/repo_quality.toml")
    return path if path.is_absolute() else repo / path


def load_config(repo: Path, config_path: Path | None = None) -> Config:
    """Load the repository-quality TOML document."""
    path = resolve_config(repo, config_path)
    if not path.is_file():
        raise QualityError(f"configuration file not found: {path}")
    try:
        with path.open("rb") as handle:
            data = tomllib.load(handle)
    except tomllib.TOMLDecodeError as exc:
        raise QualityError(f"invalid TOML in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise QualityError(f"configuration must be a TOML table: {path}")
    return data


def string_list(config: Config, key: str) -> list[str]:
    """Read a required list of strings from configuration."""
    value = config.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise QualityError(f"configuration key {key!r} must be a list of strings")
    return value


def string_value(config: Config, key: str) -> str:
    """Read a required string from configuration."""
    value = config.get(key)
    if not isinstance(value, str):
        raise QualityError(f"configuration key {key!r} must be a string")
    return value


def integer_value(config: Config, key: str) -> int:
    """Read a required positive integer from configuration."""
    value = config.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise QualityError(f"configuration key {key!r} must be a positive integer")
    return value


def safe_repo_path(repo: Path, relative: str | Path) -> Path:
    """Resolve a configured path and reject paths outside the repository."""
    path = (repo / relative).resolve()
    try:
        path.relative_to(repo.resolve())
    except ValueError as exc:
        raise QualityError(f"configured path escapes repository: {relative}") from exc
    return path


def tracked_files(repo: Path) -> list[Path]:
    """Return files tracked by Git, requiring ``repo`` to be the worktree root."""
    top = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--show-toplevel"],
        capture_output=True,
        check=False,
        text=True,
    )
    if top.returncode != 0:
        raise QualityError(f"not a Git worktree: {repo}")
    if Path(top.stdout.strip()).resolve() != repo.resolve():
        raise QualityError(f"repository path is not the Git worktree root: {repo}")
    result = subprocess.run(
        ["git", "-C", str(repo), "ls-files", "-z"],
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise QualityError("git ls-files failed")
    return [repo / os.fsdecode(item) for item in result.stdout.split(b"\0") if item]


def is_excluded(path: Path, repo: Path, excluded_dirs: set[str]) -> bool:
    """Return whether a repository-relative path enters an excluded directory."""
    return any(part in excluded_dirs for part in path.relative_to(repo).parts[:-1])
