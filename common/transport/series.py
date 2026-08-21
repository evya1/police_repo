"""End-to-end series engine over a PeerChannel.

The top of the tree: a full six-sub-game series that drives handshake, strict
thief-first alternation, at-least-once turn delivery, and a real three-layer mutual
audit over any PeerChannel (loopback for CI, FastMCP for production). The engine is
role-agnostic: it takes the natural role and the channel and derives the per-sub-game
role via ``role_for``. A failed audit settles the sub-game ``TAMPER_FORFEIT`` — both
sides zeroed, no repair path (FR-29). The per-sub-game turn loop lives in
``subgame.py`` (150-logical-line cap).
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Protocol

from common.domain.scoring import Outcome, Role, settled_outcome

DEFAULT_MAX_STEPS = 35


class Budgets(Protocol):
    """Turn budgets for the series engine."""

    turn_timeout: float
    connect_timeout: float
    poll_interval: float


class PeerConfig:
    """Configuration injected into the series engine."""

    def __init__(
        self,
        natural_role: Role,
        budgets: Budgets,
        terms: dict,
        seed: int = 0,
        locks: dict[str, str] | None = None,
    ) -> None:
        self.natural_role = natural_role
        self.budgets = budgets
        self.terms = terms
        self.seed = seed
        self.locks = locks


@dataclass
class SeriesRow:
    """One row in the series ledger."""

    sub_game_number: int
    role: Role
    outcome: Outcome
    steps: int
    score_police: int
    score_thief: int
    audit_ok: bool


@dataclass
class SeriesResult:
    """The final result of a series."""

    game_id: str
    game_uid: str
    ledger: list[SeriesRow] = field(default_factory=list)
    settled: bool = False
    settled_outcome: Outcome = Outcome.TAMPER_FORFEIT


class TurnEngine(Protocol):
    """The interface the series engine calls to get a move."""

    def start_subgame(self, sub_game: int, role: Role, terms: dict | None = None) -> None: ...
    def decide(self) -> dict: ...
    def observe_opponent(self, message: dict) -> None: ...
    def terminal(self) -> Outcome | None: ...


SubgameDriver = Callable[[object, TurnEngine, PeerConfig, int], SeriesRow]


class PeerFacade:
    """Wraps a channel and a turn engine into a peer that can both send and receive."""

    def __init__(
        self,
        channel,
        engine: TurnEngine,
        config: PeerConfig,
        name: str = "peer",
        subgame_driver: SubgameDriver | None = None,
    ) -> None:
        self.channel = channel
        self.engine = engine
        self.config = config
        self.name = name
        self._game_id = ""
        self._game_uid = ""
        self._ledgers: list[SeriesRow] = []
        self._subgame_driver = subgame_driver

    def run(self) -> SeriesResult:
        """Run a full six-sub-game series. Return the result."""
        self._exchange_greeting()
        for sub_game in range(1, 7):
            self._ledgers.append(self._play_sub_game(sub_game))
        all_passed = all(row.audit_ok for row in self._ledgers)
        last = self._ledgers[-1].outcome if self._ledgers else Outcome.TAMPER_FORFEIT
        final_outcome, settled = settled_outcome(last, audits_present=True, audits_passed=all_passed)
        return SeriesResult(
            game_id=self._game_id,
            game_uid=self._game_uid,
            ledger=self._ledgers,
            settled=settled,
            settled_outcome=final_outcome,
        )

    def _exchange_greeting(self) -> None:
        """Send our greeting and poll for the opponent's, then verify (fixed FR-13 order)."""
        from common.transport.integrity import new_nonce
        from common.transport.negotiate import our_greeting, verify_greeting

        greeting = our_greeting(
            terms=self.config.terms,
            nonce=new_nonce(),
            group_id=self.name,
            role=self.config.natural_role.value,
            sub_game_number=1,
            locks=self.config.locks,
        )
        self.channel.send_agreement(greeting)
        deadline = time.monotonic() + self.config.budgets.connect_timeout
        opponent = None
        while time.monotonic() < deadline:
            opponent = self.channel.poll_agreement()
            if opponent is not None:
                break
            time.sleep(self.config.budgets.poll_interval)
        if opponent is None:
            raise TimeoutError("opponent greeting not received")
        agreed = verify_greeting(
            opponent,
            self.config.terms,
            self.name,
            1,
            our_locks=self.config.locks,
        )
        self._game_id = agreed.game_id
        self._game_uid = agreed.game_uid

    def _play_sub_game(self, sub_game: int) -> SeriesRow:
        """Play one sub-game via the selected driver."""
        from common.transport.subgame import play_subgame

        driver = self._subgame_driver or play_subgame
        return driver(self.channel, self.engine, self.config, sub_game)


def run_series(
    channel_a,
    channel_b,
    config_a: PeerConfig,
    config_b: PeerConfig,
    engine_a: TurnEngine,
    engine_b: TurnEngine,
    subgame_driver: SubgameDriver | None = None,
) -> tuple[SeriesResult, SeriesResult]:
    """Run a series with two peers on opposite ends of a channel. Returns (a, b)."""
    facade_a = PeerFacade(channel_a, engine_a, config_a, "A", subgame_driver=subgame_driver)
    facade_b = PeerFacade(channel_b, engine_b, config_b, "B", subgame_driver=subgame_driver)
    result_a: SeriesResult | None = None
    result_b: SeriesResult | None = None
    errors: list[Exception] = []

    def run_a() -> None:
        nonlocal result_a
        try:
            result_a = facade_a.run()
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    def run_b() -> None:
        nonlocal result_b
        try:
            result_b = facade_b.run()
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    thread_a = threading.Thread(target=run_a, daemon=True)
    thread_b = threading.Thread(target=run_b, daemon=True)
    thread_a.start()
    thread_b.start()
    thread_a.join(timeout=60)
    thread_b.join(timeout=60)
    if thread_a.is_alive() or thread_b.is_alive():
        raise TimeoutError("series worker timed out / stuck")
    if errors:
        raise RuntimeError(f"series errors: {errors}")
    if result_a is None or result_b is None:
        raise RuntimeError("series worker returned no result")
    return result_a, result_b
