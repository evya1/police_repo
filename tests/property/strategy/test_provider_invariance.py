"""ADR-010 property tests: provider outcome never touches action/barrier/verdict.

Proves action, barrier, verdict, and target landmark equality across template,
provider-success, timeout, malformed, and exception paths for one identical
seed and state; proves the planned landmark describes the destination cell,
never the pre-move cell; captures the exact allowlisted request.
"""

from __future__ import annotations

import dataclasses

from common.domain.board import Board
from common.domain.rules import GameEngine
from common.domain.scoring import Role
from police_peer.belief.hints import GENERIC_FALLBACK, LANDMARK_CELLS
from police_peer.strategy.base import BrainBase
from police_peer.strategy.hint_types import (
    FallbackReason,
    HintRenderRequest,
    ProviderReply,
    TokenUsage,
)
from police_peer.strategy.hints import HintWriter

_ARENA = "New York"
_KNOWN_LANDMARKS = [*LANDMARK_CELLS[_ARENA], *GENERIC_FALLBACK]


class _FixedRng:
    """Deterministic stand-in for random.Random: fixed roll + first choice."""

    def __init__(self, roll: float) -> None:
        self._roll = roll

    def random(self) -> float:
        return self._roll

    def choice(self, seq):
        return seq[0]


class _CapturingProvider:
    """Captures the exact request it received, then behaves per `outcome`."""

    def __init__(self, outcome: str) -> None:
        self.outcome = outcome
        self.request: HintRenderRequest | None = None

    def render(self, request: HintRenderRequest, *, deadline=None):
        self.request = request
        if self.outcome == "success":
            return ProviderReply(
                text=f"I'm at {request.target_landmark}.", usage=TokenUsage(2, 2),
                provider="p", model="m",
            )
        if self.outcome == "success_unknown_usage":
            return ProviderReply(
                text=f"I'm at {request.target_landmark}.", usage=TokenUsage(None, None),
                provider="p", model="m",
            )
        if self.outcome == "timeout":
            raise TimeoutError("slow")
        if self.outcome == "malformed":
            return {"bad": "shape"}
        raise RuntimeError("boom")


class _FixedBrain(BrainBase):
    """Move selection fixed for the test; only the hint phase varies."""

    def __init__(self, action: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._action = action

    def _decide_move(self, state, belief):
        return self._action, None


def _brain(action: str, outcome: str | None) -> tuple[BrainBase, _CapturingProvider | None]:
    provider = _CapturingProvider(outcome) if outcome else None
    rng = _FixedRng(0.9)
    hw = HintWriter(Role.POLICE, rng, _ARENA, 15, provider=provider)
    brain = _FixedBrain(action, rng=rng, arena=_ARENA, max_words=15, hint_writer=hw)
    return brain, provider


def _decide_at(action: str, position, outcome: str | None):
    board = Board(size=7)
    engine = GameEngine(board=board, role=Role.POLICE, position=position)
    brain, provider = _brain(action, outcome)
    return brain.decide(engine, None, "", _ARENA), provider, brain


def _landmark_in(hint: str) -> str:
    lowered = hint.lower()
    matches = [name for name in _KNOWN_LANDMARKS if name.lower() in lowered]
    assert len(matches) == 1, f"expected exactly one landmark in {hint!r}, got {matches}"
    return matches[0]


def test_action_barrier_verdict_and_target_equal_across_provider_paths() -> None:
    outcomes = [None, "success", "timeout", "malformed", "exception"]
    results = [_decide_at("STAY", (1, 3), outcome)[0] for outcome in outcomes]

    actions = {d.action for d in results}
    barriers = {d.barrier_cell for d in results}
    verdicts = {d.verdict for d in results}
    landmarks = {_landmark_in(d.hint) for d in results}

    assert len(actions) == 1
    assert len(barriers) == 1
    assert len(verdicts) == 1
    assert len(landmarks) == 1


def test_post_move_uses_destination_not_pre_move_cell() -> None:
    """(6, 0) is truth-incompatible with every region; its MOVE:E destination
    (6, 1) is truth-compatible with "south". The hint must describe (6, 1).
    """
    decision, _, _ = _decide_at("MOVE:E", (6, 0), outcome=None)
    assert decision.action == "MOVE:E"
    assert decision.barrier_cell is None
    assert decision.verdict == "truth"
    assert _landmark_in(decision.hint) == "south"


def test_action_and_barrier_locked_before_request_is_built() -> None:
    """A provider cannot see or influence a move it did not yet know about --
    the request is built strictly after the fixed action above (STAY, None).
    """
    decision, provider, _ = _decide_at("STAY", (1, 3), outcome="success")
    assert decision.action == "STAY"
    assert decision.barrier_cell is None
    assert provider.request is not None


def test_request_captures_privacy_allowlist_only() -> None:
    """Capture the exact request; forbidden private data never appears on it."""
    _, provider, _ = _decide_at("MOVE:E", (6, 0), outcome="success")
    request = provider.request
    assert request is not None
    field_names = {f.name for f in dataclasses.fields(request)}
    assert field_names == {"role", "arena", "target_landmark", "claim", "max_words", "style"}
    assert request.target_landmark == "south"
    assert request.claim == "truth"
    assert request.arena == _ARENA
    assert request.max_words == 15
    forbidden = {"position", "cell", "grid", "belief", "scent", "legal_moves", "reasoning", "smell_grid"}
    assert not forbidden & field_names


def test_decision_seals_the_same_usage_and_fallback_reason_as_hint_writer() -> None:
    """A provider-backed turn: Decision carries exactly what say() just sealed."""
    decision, _, brain = _decide_at("STAY", (1, 3), outcome="success")
    sealed = brain.hint_writer.last_result
    assert sealed is not None
    assert decision.usage == sealed.usage == TokenUsage(2, 2)
    assert decision.fallback_reason == sealed.fallback_reason is None


def test_template_mode_seals_known_zero_usage() -> None:
    decision, _, _ = _decide_at("STAY", (1, 3), outcome=None)
    assert decision.usage == TokenUsage(0, 0)
    assert decision.fallback_reason == FallbackReason.NO_PROVIDER


def test_provider_unknown_usage_seals_none_never_fabricated() -> None:
    decision, _, _ = _decide_at("STAY", (1, 3), outcome="success_unknown_usage")
    assert decision.usage == TokenUsage(None, None)
    assert decision.fallback_reason is None


def test_forced_stay_seals_known_zero_usage_no_hint_writer_call() -> None:
    """legal == ["STAY"]: the hint writer is never consulted -- usage is a
    KNOWN zero (no call happened), not an unknown None.
    """
    brain, _ = _brain("STAY", None)
    board = Board(size=7)
    engine = GameEngine(
        board=board, role=Role.POLICE, position=(3, 3),
        barriers=[(2, 3), (4, 3), (3, 2), (3, 4)],
    )
    decision = brain.decide(engine, None, "", _ARENA)
    assert decision.fallback is True
    assert decision.usage == TokenUsage(0, 0)
    assert decision.fallback_reason is None
    assert brain.hint_writer.last_result is None
