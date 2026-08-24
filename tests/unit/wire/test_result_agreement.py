"""wire/result_agreement.exchange: one send, a bounded wait, and it never raises (CT-08)."""

from __future__ import annotations

from common.transport.kit_agreement import AgreementProposal, proposal_wire
from police_peer.wire.result_agreement import exchange


class _FakeChannel:
    def __init__(self, inbound: list[dict | None] | None = None, *, raise_on_send: bool = False):
        self.sent: list[dict] = []
        self._inbound = list(inbound or [])
        self._raise_on_send = raise_on_send

    def send_control(self, message: dict) -> dict:
        if self._raise_on_send:
            raise RuntimeError("boom")
        self.sent.append(message)
        return {"ok": True}

    def poll_control(self) -> dict | None:
        return self._inbound.pop(0) if self._inbound else None


def _proposal(sha: str = "a" * 64) -> AgreementProposal:
    return AgreementProposal(
        game_id="g", game_uid="u", consensus_sha256=sha, final_result={}, rows=[]
    )


def test_matching_digests_agree() -> None:
    ours = _proposal()
    channel = _FakeChannel(inbound=[proposal_wire(ours)])

    outcome = exchange(channel, ours, budget=1.0)

    assert outcome.agreed is True
    assert len(channel.sent) == 1
    assert channel.sent[0]["kind"] == "result_agreement"


def test_mismatched_digests_do_not_agree() -> None:
    ours = _proposal("a" * 64)
    theirs = proposal_wire(_proposal("b" * 64))
    channel = _FakeChannel(inbound=[theirs])

    outcome = exchange(channel, ours, budget=1.0)

    assert outcome.agreed is False
    assert "a" * 64 in outcome.reason
    assert "b" * 64 in outcome.reason


def test_a_silent_opponent_times_out_to_not_agreed_within_budget() -> None:
    ours = _proposal()
    channel = _FakeChannel(inbound=[])

    outcome = exchange(channel, ours, budget=0.05)

    assert outcome.agreed is False
    assert "did not arrive" in outcome.reason


def test_exchange_never_raises_when_send_fails() -> None:
    ours = _proposal()
    channel = _FakeChannel(raise_on_send=True)

    outcome = exchange(channel, ours, budget=0.05)  # must not raise

    assert outcome.agreed is False


def test_exchange_never_raises_when_poll_fails() -> None:
    ours = _proposal()

    class _PollBoom(_FakeChannel):
        def poll_control(self) -> dict | None:
            raise RuntimeError("poll boom")

    outcome = exchange(_PollBoom(), ours, budget=0.05)  # must not raise

    assert outcome.agreed is False


def test_a_wrong_kind_control_message_is_skipped_not_mistaken_for_agreement() -> None:
    ours = _proposal()
    channel = _FakeChannel(inbound=[{"kind": "receive_control_refusal"}, proposal_wire(ours)])

    outcome = exchange(channel, ours, budget=1.0)

    assert outcome.agreed is True
