"""Tests for message dataclasses and Hebrew/emoji wire round-trips.

TC-12 (unknown key tolerance) and TC-26 (Hebrew + astral-plane-emoji round-trip) exercised
through the dataclass wire API.
"""

from __future__ import annotations

import json

from common.transport.messages import (
    AuditPayload,
    ControlMessage,
    Negotiation,
    TurnMessage,
)

# --- TC-12: unknown key tolerated and ignored -----------------------------------------------


class TestTc12UnknownKey:
    """TC-12: unknown key is tolerated and ignored (extension seam, FR-20)."""

    def test_turn_from_wire_drops_unknown_keys(self) -> None:
        raw = {
            "step": 1,
            "sender": "thief",
            "hint": "hi",
            "smell_grid": {},
            "commit": "a" * 64,
            "timestamp": "now",
            "future_field": 42,
        }
        msg = TurnMessage.from_wire(raw)
        assert not hasattr(msg, "future_field") or getattr(msg, "future_field", None) is None

    def test_control_from_wire_drops_unknown_keys(self) -> None:
        raw = {
            "kind": "status",
            "sender": "police",
            "extra_key": 99,
        }
        msg = ControlMessage.from_wire(raw)
        assert msg.kind == "status"
        assert not hasattr(msg, "extra_key") or getattr(msg, "extra_key", None) is None

    def test_audit_from_wire_drops_unknown_keys(self) -> None:
        raw = {
            "sender": "thief",
            "records": [],
            "result_claim": "survival",
            "future_field": "ignored",
        }
        msg = AuditPayload.from_wire(raw)
        assert msg.sender == "thief"
        assert not hasattr(msg, "future_field") or getattr(msg, "future_field", None) is None

    def test_negotiation_from_wire_drops_unknown_keys(self) -> None:
        raw = {
            "terms": {},
            "nonce": "n",
            "signature": "s",
            "group_id": "g",
            "future_field": "ignored",
        }
        msg = Negotiation.from_wire(raw)
        assert msg.group_id == "g"
        assert not hasattr(msg, "future_field") or getattr(msg, "future_field", None) is None


# --- TC-26: Hebrew + astral-plane-emoji hint round-trips under ensure_ascii=False ------------


class TestTc26HebrewEmojiRoundTrip:
    """TC-26: Hebrew + astral-plane-emoji hint round-trips the wire byte-identical under
    ensure_ascii=False.
    """

    def test_hebrew_hint_roundtrips(self) -> None:
        hint = "אני חושב שהם צפונה"
        turn = TurnMessage(
            step=1, sender="thief", hint=hint,
            smell_grid={"0,0": 0.5}, commit="a" * 64, timestamp="now",
        )
        wire = turn.to_wire()
        raw = json.dumps(wire, ensure_ascii=False)
        assert hint in raw
        assert "\\u" not in raw

    def test_emoji_hint_roundtrips(self) -> None:
        hint = "🌀🔮✨ I see them moving ✨🔮🌀"
        turn = TurnMessage(
            step=2, sender="police", hint=hint,
            smell_grid={}, commit="b" * 64, timestamp="now",
        )
        wire = turn.to_wire()
        raw = json.dumps(wire, ensure_ascii=False)
        assert hint in raw
        assert "\\u" not in raw

    def test_hebrew_and_emoji_combined(self) -> None:
        hint = "🌀 מערב צפון-מזרח ✨"
        turn = TurnMessage(
            step=3, sender="thief", hint=hint,
            smell_grid={"1,1": 0.7}, commit="c" * 64, timestamp="now",
        )
        wire = turn.to_wire()
        raw = json.dumps(wire, ensure_ascii=False)
        assert hint in raw
        assert "\\u" not in raw

    def test_wire_shape_preserves_hebrew_exact_bytes(self) -> None:
        hint = "אני אוהב את המשחק הזה"
        turn = TurnMessage(
            step=1, sender="thief", hint=hint,
            smell_grid={}, commit="d" * 64, timestamp="now",
        )
        wire = turn.to_wire()
        assert wire["hint"] == hint
        round_tripped = TurnMessage.from_wire(wire)
        assert round_tripped.hint == hint

    def test_negotiation_omits_none_fields(self) -> None:
        msg = Negotiation(terms={}, nonce="n", signature="s", group_id="g")
        wire = msg.to_wire()
        assert "role" not in wire
        assert "sub_game_number" not in wire
        assert "game_uid" not in wire
        assert "scent_model_sha256" not in wire

    def test_turn_to_wire_includes_null_optionals(self) -> None:
        turn = TurnMessage(
            step=1, sender="thief", hint="hi",
            smell_grid={}, commit="a" * 64, timestamp="now",
        )
        wire = turn.to_wire()
        assert "barrier_placed" in wire
        assert wire["barrier_placed"] is None
