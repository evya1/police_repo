"""BLOCKER-1: the runner must not force the legacy stand-in on production.

``run_one_peer`` is the CLI's only path into ``create_peer``, so the regression belongs at
that boundary and not only in the SDK unit test: an omitted ``strategy`` has to reach the
composition root as ``None`` (which is what selects the real ``PoliceBrain``), and an
explicit ``Strategy`` has to arrive by identity so the documented legacy override survives.

Every collaborator around that one call is faked — no server is started and no socket is
opened just to observe argument pass-through.
"""

from __future__ import annotations

import pytest

from common.domain.scoring import Role
from police_peer import runner
from police_peer.strategy import BaselineStrategy


class _StubChannel:
    def __init__(self, *args: object, **kwargs: object) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


class _StubResult:
    settled = True


class _StubFacade:
    def run(self) -> _StubResult:
        return _StubResult()


@pytest.fixture
def spy(monkeypatch: pytest.MonkeyPatch) -> dict:
    """Neutralize the transport around ``create_peer`` and record its keyword arguments."""
    calls: dict = {}

    def fake_create_peer(**kwargs: object) -> _StubFacade:
        calls.update(kwargs)
        return _StubFacade()

    monkeypatch.setattr(runner, "serve_background", lambda *a, **k: None)
    monkeypatch.setattr(runner, "edge_answers", lambda *a, **k: True)
    monkeypatch.setattr(runner, "McpChannel", _StubChannel)
    monkeypatch.setattr(runner, "create_peer", fake_create_peer)
    return calls


def test_omitted_strategy_reaches_create_peer_as_none(spy: dict) -> None:
    assert runner.run_one_peer() == 0
    assert "strategy" in spy
    assert spy["strategy"] is None


def test_explicit_strategy_reaches_create_peer_by_identity(spy: dict) -> None:
    override = BaselineStrategy()
    assert runner.run_one_peer(strategy=override) == 0
    assert spy["strategy"] is override


def test_runner_passes_the_shipped_config_paths_through(spy: dict) -> None:
    runner.run_one_peer(shared_config="config/game.json", private_config="config/game.toml")
    assert spy["config_path"] == "config/game.json"
    assert spy["private_config_path"] == "config/game.toml"
    assert spy["role"] is Role.POLICE
