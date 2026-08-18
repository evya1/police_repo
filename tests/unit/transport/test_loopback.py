"""Tests for the loopback transport.

TC-01 / TC-02: assert the four tool names and the argument-name asymmetry.
"""

from __future__ import annotations

from common.transport.loopback import Inboxes, LoopbackPeer, LoopbackTransport, pair


class TestInboxes:
    """Tests for the Inboxes data structure."""

    def test_init_creates_four_deques(self) -> None:
        inboxes = Inboxes()
        assert hasattr(inboxes, "agreements")
        assert hasattr(inboxes, "turns")
        assert hasattr(inboxes, "audits")
        assert hasattr(inboxes, "controls")

    def test_drain_clears_all_queues(self) -> None:
        inboxes = Inboxes()
        inboxes.agreements.append({"a": 1})
        inboxes.turns.append({"b": 2})
        inboxes.audits.append({"c": 3})
        inboxes.controls.append({"d": 4})
        inboxes.drain()
        assert len(inboxes.agreements) == 0
        assert len(inboxes.turns) == 0
        assert len(inboxes.audits) == 0
        assert len(inboxes.controls) == 0


class TestLoopbackPeer:
    """Tests for the LoopbackPeer callable surface."""

    def test_init(self) -> None:
        peer = LoopbackPeer("A")
        assert peer.name == "A"
        assert isinstance(peer.inboxes, Inboxes)

    def test_negotiate_appends_to_agreements(self) -> None:
        peer = LoopbackPeer("A")
        result = peer.negotiate({"terms": {}})
        assert result == {"ok": True}
        assert len(peer.inboxes.agreements) == 1
        assert peer.inboxes.agreements[0] == {"terms": {}}

    def test_receive_turn_appends_to_turns(self) -> None:
        peer = LoopbackPeer("A")
        result = peer.receive_turn({"step": 1})
        assert result == {"ok": True}
        assert len(peer.inboxes.turns) == 1

    def test_submit_audit_appends_to_audits(self) -> None:
        peer = LoopbackPeer("A")
        result = peer.submit_audit({"records": []})
        assert result == {"ok": True}
        assert len(peer.inboxes.audits) == 1

    def test_receive_control_appends_to_controls(self) -> None:
        peer = LoopbackPeer("A")
        result = peer.receive_control({"kind": "quit"})
        assert result == {"ok": True}
        assert len(peer.inboxes.controls) == 1

    def test_all_four_tools_return_ok(self) -> None:
        peer = LoopbackPeer("A")
        assert peer.negotiate({}) == {"ok": True}
        assert peer.receive_turn({}) == {"ok": True}
        assert peer.submit_audit({}) == {"ok": True}
        assert peer.receive_control({}) == {"ok": True}


class TestLoopbackTransport:
    """Tests for the LoopbackTransport channel."""

    def test_send_agreement_delivers_to_theirs_negotiate(self) -> None:
        a, b = pair("A", "B")
        result = a.send_agreement({"terms": {}})
        assert result == {"ok": True}
        # B should have received it in their agreements inbox
        msg = b.poll_agreement()
        assert msg == {"terms": {}}

    def test_send_turn_delivers_to_theirs_receive_turn(self) -> None:
        a, b = pair("A", "B")
        result = a.send_turn({"step": 1})
        assert result == {"ok": True}
        msg = b.poll_turn()
        assert msg == {"step": 1}

    def test_send_audit_delivers_to_theirs_submit_audit(self) -> None:
        a, b = pair("A", "B")
        result = a.send_audit({"records": []})
        assert result == {"ok": True}
        msg = b.poll_audit()
        assert msg == {"records": []}

    def test_send_control_delivers_to_theirs_receive_control(self) -> None:
        a, b = pair("A", "B")
        result = a.send_control({"kind": "status"})
        assert result == {"ok": True}
        msg = b.poll_control()
        assert msg == {"kind": "status"}

    def test_poll_returns_none_when_empty(self) -> None:
        a, b = pair("A", "B")
        assert a.poll_agreement() is None
        assert a.poll_turn() is None
        assert a.poll_audit() is None
        assert a.poll_control() is None

    def test_argument_name_asymmetry(self) -> None:
        """TC-01/TC-02: assert the payload/message asymmetry at the loopback surface."""
        a, b = pair("A", "B")
        # negotiate takes `message`
        a.send_agreement({"terms": {}})
        # submit_audit takes `payload`
        a.send_audit({"records": []})
        # Verify the messages landed in the right inboxes
        assert b.poll_agreement() == {"terms": {}}
        assert b.poll_audit() == {"records": []}


class TestPair:
    """Tests for the pair() factory."""

    def test_pair_creates_mutual_transport(self) -> None:
        a, b = pair()
        assert isinstance(a, LoopbackTransport)
        assert isinstance(b, LoopbackTransport)
        # a sends to b, b sends to a
        a.send_turn({"step": 1})
        msg = b.poll_turn()
        assert msg == {"step": 1}
        b.send_turn({"step": 2})
        msg = a.poll_turn()
        assert msg == {"step": 2}

    def test_pair_with_names(self) -> None:
        a, b = pair("Police", "Thief")
        assert a.ours.name == "Police"
        assert b.ours.name == "Thief"
