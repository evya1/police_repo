"""Frozen per-subgame replay evidence (RP-06, OBS-006, SEC-005, SEC-006).

``capture_subgame_evidence`` is an *observation* of values a finished sub-game already
produced — the step-0-prefixed audit record list just sent, the opponent's revealed
records, and the opponent-commitment ledger already consumed by the live audit. It adds
no state machine and changes no message, audit, or settlement order. Opponent-supplied
records are decoded defensively (a hostile peer must never crash a legal game); our own
records are ours and are decoded the same defensive way as a matter of course.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Protocol

from common.transport.canonical import canonical_bytes
from common.transport.replay_records import decode_half
from common.transport.replay_types import ReplayIssue, SealedRecord

if TYPE_CHECKING:
    from common.transport.series import PeerConfig, SeriesRow, TurnEngine


@dataclass(frozen=True, slots=True)
class SubgameReplayEvidence:
    """Everything an offline verifier needs to rehash and rebind one played sub-game.

    ``game_id``/``game_uid`` start empty — identity lives on ``PeerFacade``, not inside
    ``play_subgame`` — and are attached by the facade via ``dataclasses.replace`` once
    the greeting has resolved. ``observed_opponent_commitments`` is the ordered, immutable
    snapshot of ``Inbox.played`` taken after the live audit consumed it: the anchor that
    arms offline live-binding coverage.
    """

    sub_game_index: int
    terms_bytes: bytes
    own_records: tuple[SealedRecord, ...]
    opponent_records: tuple[SealedRecord, ...]
    observed_opponent_commitments: tuple[tuple[int, str], ...]
    our_result_claim: str
    opponent_result_claim: str | None
    row: SeriesRow
    game_id: str = ""
    game_uid: str = ""
    capture_issues: tuple[str, ...] = ()


class SubgameDriver(Protocol):
    """The callable ``PeerFacade._play_sub_game`` invokes for one sub-game.

    ``evidence_sink`` is keyword-only and always passed by the facade (never
    conditionally) — a conforming driver must accept it, even to ignore it.
    """

    def __call__(
        self,
        channel: object,
        engine: TurnEngine,
        config: PeerConfig,
        sub_game: int,
        *,
        evidence_sink: Callable[[SubgameReplayEvidence], None] | None = None,
    ) -> SeriesRow: ...


class EvidenceCollector:
    """Accumulates one series' per-sub-game replay evidence, in sub-game order.

    ``play_subgame`` builds each ``SubgameReplayEvidence`` before the greeting
    handshake has resolved identity, so the collector is constructed only after
    ``PeerFacade`` has ``game_id``/``game_uid`` in hand and attaches them to every
    entry as it comes in. ``capture`` is the ``evidence_sink`` callback a
    ``SubgameDriver`` invokes.
    """

    def __init__(self, game_id: str, game_uid: str) -> None:
        self._game_id = game_id
        self._game_uid = game_uid
        self._entries: list[SubgameReplayEvidence] = []

    def capture(self, evidence: SubgameReplayEvidence) -> None:
        """Attach the bound identity to ``evidence`` and accumulate it."""
        self._entries.append(replace(evidence, game_id=self._game_id, game_uid=self._game_uid))

    def finish(self) -> tuple[SubgameReplayEvidence, ...]:
        """Return the accumulated entries, in the order they were captured."""
        return tuple(self._entries)


def default_subgame_driver(audit_wire: object | None = None) -> SubgameDriver:
    """Return the production ``play_subgame`` driver, imported lazily to avoid a cycle.

    ``subgame.py`` imports ``series.py`` at module level, so ``series.py`` cannot import
    ``play_subgame`` back at its own module level without a circular import.

    ``audit_wire`` is the injected audit-wire adapter (T054). Omitting it keeps the
    internal lane, which is what every existing caller means.
    """
    from common.transport.subgame import play_subgame

    if audit_wire is None:
        return play_subgame

    def _driver(channel, engine, config, sub_game, *, evidence_sink=None):
        return play_subgame(
            channel, engine, config, sub_game,
            evidence_sink=evidence_sink, audit_wire=audit_wire,
        )

    return _driver


def _issue_text(issue: ReplayIssue) -> str:
    """Render one decode/sequence issue as one plain-text capture-issue entry."""
    step = f" step={issue.step}" if issue.step is not None else ""
    half = f" half={issue.half}" if issue.half is not None else ""
    return f"{issue.code}: {issue.message}{step}{half}"


def _decode_side(raw_records: object, half: str) -> tuple[tuple[SealedRecord, ...], list[str]]:
    """Decode one half defensively: never raise, report what did not decode instead."""
    try:
        records, issues = decode_half(raw_records, half)
    except Exception as exc:  # noqa: BLE001 - capture must never crash a live game
        return (), [f"capture_error: {half}: {exc}"]
    return tuple(records), [_issue_text(issue) for issue in issues]


def capture_subgame_evidence(
    *,
    sub_game_index: int,
    terms: dict,
    own_records_raw: list[dict],
    opponent_records_raw: object,
    observed_opponent_commitments: Mapping[int, str],
    our_result_claim: str,
    opponent_result_claim: str | None,
    row: SeriesRow,
) -> SubgameReplayEvidence:
    """Build the frozen replay evidence for one finished sub-game.

    ``own_records_raw`` must already be the step-0-prefixed list (``audit_payload``'s
    ``records``), not the raw in-loop accumulator. ``observed_opponent_commitments`` is
    copied here (never retained as the caller's own dict) — pass it only after the live
    audit has read ``Inbox.played``, so mutating the caller's map afterward cannot reach
    this sealed evidence.
    """
    own_records, own_issues = _decode_side(own_records_raw, "own")
    opponent_records, opponent_issues = _decode_side(opponent_records_raw, "opponent")
    commitments = tuple(sorted((int(step), commit) for step, commit in observed_opponent_commitments.items()))
    return SubgameReplayEvidence(
        sub_game_index=sub_game_index,
        terms_bytes=canonical_bytes(terms),
        own_records=own_records,
        opponent_records=opponent_records,
        observed_opponent_commitments=commitments,
        our_result_claim=our_result_claim,
        opponent_result_claim=opponent_result_claim,
        row=row,
        capture_issues=tuple(own_issues) + tuple(opponent_issues),
    )
