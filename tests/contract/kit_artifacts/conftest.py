"""Shared access to the pinned kit reference bundle (see its PROVENANCE.md)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2] / "fixtures" / "kit_reference"
_GAME_ID = "team-aleph-vs-team-bet"


def _load(name: str) -> dict:
    return json.loads((_ROOT / name).read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def kit_game_id() -> str:
    return _GAME_ID


@pytest.fixture(scope="session")
def kit_result() -> dict:
    return _load(f"result_{_GAME_ID}.json")


@pytest.fixture(scope="session")
def kit_declaration() -> dict:
    return _load(f"declaration_{_GAME_ID}.json")


@pytest.fixture(scope="session")
def kit_config() -> dict:
    return _load(f"config_{_GAME_ID}_g01.json")


@pytest.fixture(scope="session")
def kit_log() -> dict:
    return _load(f"log_{_GAME_ID}_g01.json")
