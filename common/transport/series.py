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

from dataclasses import dataclass, field
from typing import Protocol

from common.domain.scoring import Outcome, Role, settled_outcome
from common.transport import replay_evidence as _replay_evidence
from common.transport.opponent_pin import OpponentPin
from common.transport.replay_evidence import SubgameDriver, SubgameReplayEvidence
from common.transport.series_greeting import exchange_series_greeting

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
        mode: str = "warmup",
        identity_block: dict | None = None,
    ) -> None:
        self.natural_role = natural_role
        self.budgets = budgets
        self.terms = terms
        self.seed = seed
        self.locks = locks
        self.mode = mode
        self.identity_block = identity_block


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
    # The opponent's group id, as the greeting resolved it. `game_id` is the SORTED pair, so it
    # cannot say which half is theirs -- and every per-group projection (scores, roles, tokens,
    # repo links) needs to. Our own id is configuration the caller already holds, so only the
    # discovered half is carried here.
    opponent_group_id: str = ""
    # The optional, public subset the opponent actually declared in its greeting.  Missing
    # fields stay missing; they are never filled from our local assumptions.
    opponent_identity: dict | None = None
    ledger: list[SeriesRow] = field(default_factory=list)
    settled: bool = False
    settled_outcome: Outcome = Outcome.TAMPER_FORFEIT
    replay_evidence: tuple[SubgameReplayEvidence, ...] = ()


class TurnEngine(Protocol):
    """The interface the series engine calls to get a move."""

    def start_subgame(self, sub_game: int, role: Role, terms: dict | None = None) -> None: ...
    def decide(self) -> dict: ...
    def observe_opponent(self, message: dict) -> None: ...
    def terminal(self) -> Outcome | None: ...
    def terminal_final(self) -> dict | None:
        """Payload of the game-ending final step owed after settling, or None.

        A thief that saw its own capture (rules 46/47 — a fact only the thief can see)
        owes a concession: a STAY carrying claim_response {"claim": own cell, "caught": true}.
        A police settling from the thief's final owes a plain sealed STAY. Without the
        concession the cop waits out its budget and two honest reports fork (rule 35).
        """


class PeerFacade:
    """Wraps a channel and a turn engine into a peer that can both send and receive."""

    def __init__(
        self,
        channel,
        engine: TurnEngine,
        config: PeerConfig,
        name: str = "peer",
        subgame_driver: SubgameDriver | None = None,
        mode: str | None = None,
        opponent_pin: OpponentPin | None = None,
    ) -> None:
        self.channel = channel
        self.engine = engine
        self.config = config
        self.name = name
        self.mode = mode or getattr(config, "mode", "warmup")
        # T054: ONE pin per series. The composition root hands the same object to the
        # per-sub-game negotiation driver, so sub-game 1's verified opponent -- learned
        # right here -- is the one sub-games 2-6 are compared against.
        self._opponent_pin = opponent_pin if opponent_pin is not None else OpponentPin()
        self._game_id = self._game_uid = self._opponent_group_id = ""
        self._opponent_identity: dict | None = None
        self._ledgers: list[SeriesRow] = []
        self._subgame_driver = subgame_driver or _replay_evidence.default_subgame_driver()

    def run(self) -> SeriesResult:
        """Run a full six-sub-game series. Return the result."""
        self._exchange_greeting()
        evidence = _replay_evidence.EvidenceCollector(self._game_id, self._game_uid)
        for sub_game in range(1, 7):
            row = self._subgame_driver(
                self.channel, self.engine, self.config, sub_game, evidence_sink=evidence.capture
            )
            self._ledgers.append(row)
        all_passed = all(row.audit_ok for row in self._ledgers)
        last = self._ledgers[-1].outcome if self._ledgers else Outcome.TAMPER_FORFEIT
        final_outcome, settled = settled_outcome(last, audits_present=True, audits_passed=all_passed)
        return SeriesResult(
            game_id=self._game_id,
            game_uid=self._game_uid,
            opponent_group_id=self._opponent_group_id,
            opponent_identity=self._opponent_identity,
            ledger=self._ledgers,
            settled=settled,
            settled_outcome=final_outcome,
            replay_evidence=evidence.finish(),
        )

    def _exchange_greeting(self) -> None:
        """Send our greeting and poll for the opponent's, then verify (fixed FR-13 order)."""
        resolved = exchange_series_greeting(
            self.channel, self.config, self.name, self._opponent_pin,
        )
        (self._game_id, self._game_uid, self._opponent_group_id,
         self._opponent_identity) = resolved


# ``run_series`` (the two-peer harness that drives both ends of one channel) lives in its
# own module so this one stays at the engine itself; re-exported here because it has always
# been part of this module's public surface.
from common.transport.run_series import run_series  # noqa: E402, F401
