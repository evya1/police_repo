"""Unit tests for the ported state machine (kit sparring/tests/test_wire_contract.py)."""

from __future__ import annotations

import unittest

from common.transport.state import IllegalTransition, PeerState, PeerStateMachine


class TestStateMachine(unittest.TestCase):
    def test_the_happy_path(self):
        m = PeerStateMachine()
        for target in (PeerState.COMPUTING_MOVE, PeerState.COMMITTING, PeerState.AWAITING_REVEAL,
                       PeerState.VERIFYING, PeerState.WAITING_FOR_OPPONENT):
            m.to(target)
        self.assertIs(m.state, PeerState.WAITING_FOR_OPPONENT)

    def test_illegal_transitions_are_rejected(self):
        m = PeerStateMachine()
        with self.assertRaises(IllegalTransition):
            m.to(PeerState.VERIFYING)

    def test_technical_loss_is_absorbing(self):
        m = PeerStateMachine()
        m.fail()
        self.assertTrue(m.finished)
        with self.assertRaises(IllegalTransition):
            m.to(PeerState.COMPUTING_MOVE)
