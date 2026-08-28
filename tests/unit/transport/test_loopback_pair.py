"""Pair-factory tests split from the four-tool loopback contract."""

from common.transport.loopback import LoopbackTransport, pair


def test_pair_creates_mutual_transport() -> None:
    a, b = pair()
    assert isinstance(a, LoopbackTransport)
    assert isinstance(b, LoopbackTransport)
    a.send_turn({"step": 1})
    assert b.poll_turn() == {"step": 1}
    b.send_turn({"step": 2})
    assert a.poll_turn() == {"step": 2}


def test_pair_with_names() -> None:
    a, b = pair("Police", "Thief")
    assert a.ours.name == "Police"
    assert b.ours.name == "Thief"
