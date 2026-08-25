from types import SimpleNamespace

from common.domain.scoring import Outcome, Role
from police_peer.live_events import ObservableTurnEngine, observe_driver


class _Belief:
    def as_matrix(self) -> list[list[float]]:
        return [[0.25, 0.75], [0.0, 0.0]]


class _Engine:
    def __init__(self) -> None:
        game = SimpleNamespace(
            board=SimpleNamespace(size=2), role=Role.POLICE, position=(1, 0),
            step=3, barriers=[(0, 1)],
        )
        self._session = SimpleNamespace(engine=game)
        self._belief, self._sub_game = _Belief(), 2
        self._last_opponent_hint = "near Manhattan"

    def start_subgame(self, sub_game, role, terms=None) -> None:
        self._sub_game, self._session.engine.role = sub_game, role

    def decide(self) -> dict:
        return {"move": "MOVE:E", "hint": "search downtown", "verdict": "non_claim"}

    def observe_opponent(self, message: dict) -> None:
        self._last_opponent_hint = message["hint"]

    def terminal(self):
        return Outcome.SURVIVAL

    def terminal_final(self) -> None:
        return None


def test_observer_emits_only_local_truth_and_proxies_engine() -> None:
    events: list[dict] = []
    engine = ObservableTurnEngine(_Engine(), events.append)
    engine.start_subgame(4, Role.POLICE, terms={})
    assert engine.decide()["move"] == "MOVE:E"
    engine.observe_opponent({"hint": "near Bronx"})
    assert engine.terminal() is Outcome.SURVIVAL
    assert [event["phase"] for event in events] == [
        "SUB-GAME STARTED", "MOVE SEALED", "OPPONENT TURN VERIFIED",
    ]
    assert events[-1]["belief"] == [[0.25, 0.75], [0.0, 0.0]]
    assert events[-1]["opponent_hint"] == "near Bronx"
    assert all("opponent_position" not in event for event in events)


def test_broken_listener_cannot_break_play() -> None:
    def broken(_event: dict) -> None:
        raise RuntimeError("display closed")

    engine = ObservableTurnEngine(_Engine(), broken)
    assert engine.decide()["move"] == "MOVE:E"


def test_driver_emits_audited_subgame_score() -> None:
    events: list[dict] = []

    def driver(_channel, _engine, _config, sub_game, *, evidence_sink=None):
        del sub_game, evidence_sink
        return SimpleNamespace(
            score_police=20, score_thief=5, outcome=Outcome.CAPTURE, audit_ok=True,
        )

    wrapped = observe_driver(driver, events.append)
    row = wrapped(None, ObservableTurnEngine(_Engine(), events.append), None, 1)
    assert row.outcome is Outcome.CAPTURE
    assert events[-1]["score"] == "Police 20 — Thief 5"
    assert events[-1]["audit"] == "PASSED"
