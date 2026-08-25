"""Read-only live observations emitted by the repository's real turn engine."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import suppress
from typing import Any

LiveListener = Callable[[dict[str, Any]], None]


def _snapshot(engine: Any, phase: str, payload: dict | None = None) -> dict[str, Any]:
    session = getattr(engine, "_session", None)
    game = getattr(session, "engine", None)
    belief = getattr(engine, "_belief", None)
    size = getattr(getattr(game, "board", None), "size", 7)
    matrix = belief.as_matrix() if belief is not None else [[0.0] * size for _ in range(size)]
    event: dict[str, Any] = {
        "kind": "turn_lock" if phase != "SUB-GAME STARTED" else "lifecycle",
        "phase": phase,
        "sub_game": getattr(engine, "_sub_game", 0),
        "role": getattr(getattr(game, "role", None), "value", "police"),
        "position": list(getattr(game, "position", (0, 0))),
        "step": getattr(game, "step", 0),
        "barriers": [list(cell) for cell in getattr(game, "barriers", [])],
        "belief": matrix,
        "opponent_hint": getattr(engine, "_last_opponent_hint", ""),
    }
    if payload:
        event.update({key: payload.get(key) for key in ("move", "hint", "verdict")})
    return event


class ObservableTurnEngine:
    """Transparent TurnEngine decorator that publishes local-truth GUI events."""

    def __init__(self, engine: Any, listener: LiveListener) -> None:
        self._engine, self._listener = engine, listener

    def _notify(self, phase: str, payload: dict | None = None) -> None:
        with suppress(Exception):  # GUI failure must never alter play
            self._listener(_snapshot(self._engine, phase, payload))

    def start_subgame(self, sub_game: int, role: Any, terms: dict | None = None) -> None:
        self._engine.start_subgame(sub_game, role, terms=terms)
        self._notify("SUB-GAME STARTED")

    def decide(self) -> dict:
        payload = self._engine.decide()
        self._notify("MOVE SEALED", payload)
        return payload

    def observe_opponent(self, message: dict) -> None:
        self._engine.observe_opponent(message)
        self._notify("OPPONENT TURN VERIFIED")

    def terminal(self):
        return self._engine.terminal()

    def terminal_final(self) -> dict | None:
        payload = self._engine.terminal_final()
        if payload is not None:
            self._notify("TERMINAL MOVE SEALED", payload)
        return payload


def observe(engine: Any, listener: LiveListener | None) -> Any:
    """Decorate only GUI-enabled engines; keep the normal SDK shape unchanged."""
    return ObservableTurnEngine(engine, listener) if listener is not None else engine


def observe_driver(driver: Any, listener: LiveListener | None) -> Any:
    """Add audited sub-game score events without changing the transport driver."""
    if listener is None:
        return driver

    def wrapped(channel, engine, config, sub_game, *, evidence_sink=None):
        row = driver(
            channel, engine, config, sub_game, evidence_sink=evidence_sink,
        )
        raw = getattr(engine, "_engine", engine)
        event = _snapshot(raw, "SUB-GAME SETTLED")
        event.update(
            score=f"Police {row.score_police} — Thief {row.score_thief}",
            result=row.outcome.value, audit="PASSED" if row.audit_ok else "FAILED",
        )
        with suppress(Exception):
            listener(event)
        return row

    return wrapped
