"""Tests for the optional counter-signed negotiation tool result."""

from common.domain.scoring import Role
from common.transport.greeting_reply import counter_signed_reply_builder
from common.transport.negotiate import our_greeting
from tests.unit.transport.test_negotiate import TestOurGreeting


def test_counter_signed_reply_matches_live_interop_vector(monkeypatch) -> None:
    terms = TestOurGreeting()._terms()
    monkeypatch.setattr("common.transport.greetings.new_nonce", lambda: "0" * 32)
    reply = counter_signed_reply_builder(
        terms=terms, group_id="ZeroOne0", natural_role=Role.THIEF
    )
    incoming = our_greeting(
        terms=terms,
        nonce="a" * 32,
        group_id="aviayeli",
        role="police",
        sub_game_number=1,
    )

    result = reply(incoming)

    assert result["status"] == "accepted"
    assert result["accepted"] is True
    assert result["ok"] is True
    assert result["terms"] == terms
    assert result["nonce"] == "0" * 32
    assert result["signature"] == (
        "7d9bfbe4fee886fea372c09b86a6f4377af47b01e87f0fd46d562afb08935e3e"
    )
    assert result["identity"]["group_id"] == "ZeroOne0"
    assert result["sub_game_number"] == 1
    assert result["role"] == "thief"
    assert reply(incoming)["nonce"] == result["nonce"]


def test_counter_signed_reply_accepts_zero_as_read_only_probe() -> None:
    terms = TestOurGreeting()._terms()
    reply = counter_signed_reply_builder(
        terms=terms, group_id="ZeroOne0", natural_role=Role.THIEF
    )
    incoming = our_greeting(
        terms=terms,
        nonce="a" * 32,
        group_id="aviayeli",
        role="police",
        sub_game_number=0,
    )

    result = reply(incoming)

    assert result["accepted"] is True
    assert result["sub_game_number"] == 0
    assert result["role"] == "thief"
