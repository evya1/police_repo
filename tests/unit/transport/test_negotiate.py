"""Tests for negotiation: our_greeting — building the outgoing greeting.

FR-15: game_uid is derived, not exchanged — omitted on first contact, declared
once the opponent is known. FR-20: None fields (locks, uid) are omitted from the
wire dict. Verification order (FR-13/14/16) is covered in test_negotiate_verify.py.
"""

from __future__ import annotations

from common.domain.scoring import Role
from common.transport.ids import game_uid, terms_signature
from common.transport.negotiate import counter_signed_reply_builder, our_greeting


class TestOurGreeting:
    """Tests for our_greeting — builds an outgoing negotiation greeting."""

    def _terms(self) -> dict:
        return {
            "board_size": 7,
            "smell_grid_size": 5,
            "decay_per_step": 0.1,
            "emit_intensity": 0.9,
            "min_center_intensity": 0.5,
            "max_steps": 35,
            "barriers_max": 14,
            "setting": "New York",
            "hint_max_words": 15,
            "axis_origin_corner": "top-left",
            "axis_start_index": 0,
            "thief_start": [3, 3],
            "cop_start": [0, 0],
            "num_games": 6,
        }

    def test_returns_dict(self) -> None:
        greeting = our_greeting(
            terms=self._terms(),
            nonce="test-nonce",
            group_id="team-a",
            role="police",
            sub_game_number=1,
        )
        assert isinstance(greeting, dict)

    def test_contains_required_keys(self) -> None:
        greeting = our_greeting(
            terms=self._terms(),
            nonce="test-nonce",
            group_id="team-a",
            role="police",
            sub_game_number=1,
        )
        assert "terms" in greeting
        assert "nonce" in greeting
        assert "signature" in greeting
        assert "group_id" in greeting
        assert "role" in greeting
        assert "sub_game_number" in greeting

    def test_signature_matches_ours(self) -> None:
        terms = self._terms()
        nonce = "test-nonce"
        greeting = our_greeting(
            terms=terms, nonce=nonce, group_id="team-a",
            role="police", sub_game_number=1,
        )
        assert greeting["signature"] == terms_signature(terms, nonce)

    def test_role_is_present(self) -> None:
        greeting = our_greeting(
            terms=self._terms(),
            nonce="n",
            group_id="a",
            role="thief",
            sub_game_number=2,
        )
        assert greeting["role"] == "thief"

    def test_sub_game_number_present(self) -> None:
        greeting = our_greeting(
            terms=self._terms(),
            nonce="n",
            group_id="a",
            role="police",
            sub_game_number=3,
        )
        assert greeting["sub_game_number"] == 3

    def test_game_uid_omitted_when_no_opponent(self) -> None:
        """FR-15: game_uid is omitted on first contact (no opponent known)."""
        greeting = our_greeting(
            terms=self._terms(),
            nonce="n",
            group_id="a",
            role="police",
            sub_game_number=1,
        )
        assert "game_uid" not in greeting

    def test_game_uid_declared_when_opponent_known(self) -> None:
        """FR-15: game_uid is derived when opponent is known."""
        terms = self._terms()
        greeting = our_greeting(
            terms=terms, nonce="n", group_id="a",
            role="police", sub_game_number=2, opponent_group="b",
        )
        assert "game_uid" in greeting
        expected_uid = game_uid(terms, "a", "b")
        assert greeting["game_uid"] == expected_uid

    def test_locks_omitted_when_not_declared(self) -> None:
        """FR-20: None lock fields are omitted from the wire."""
        greeting = our_greeting(
            terms=self._terms(),
            nonce="n",
            group_id="a",
            role="police",
            sub_game_number=1,
        )
        assert "scent_model_sha256" not in greeting
        assert "wire_shape_sha256" not in greeting
        assert "info_mode_sha256" not in greeting
        assert "smell_binding_sha256" not in greeting

    def test_locks_present_when_declared(self) -> None:
        locks = {"scent_model": "abc", "wire_shape": "def"}
        greeting = our_greeting(
            terms=self._terms(),
            nonce="n",
            group_id="a",
            role="police",
            sub_game_number=1,
            locks=locks,
        )
        assert greeting["scent_model_sha256"] == "abc"
        assert greeting["wire_shape_sha256"] == "def"
        assert "info_mode_sha256" not in greeting


def test_counter_signed_reply_matches_live_interop_vector(monkeypatch) -> None:
    terms = TestOurGreeting()._terms()
    monkeypatch.setattr("common.transport.negotiate.new_nonce", lambda: "0" * 32)
    reply = counter_signed_reply_builder(
        terms=terms, group_id="ZeroOne0", natural_role=Role.THIEF,
    )
    incoming = our_greeting(
        terms=terms, nonce="a" * 32, group_id="aviayeli",
        role="police", sub_game_number=1,
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
        terms=terms, group_id="ZeroOne0", natural_role=Role.THIEF,
    )
    incoming = our_greeting(
        terms=terms, nonce="a" * 32, group_id="aviayeli",
        role="police", sub_game_number=0,
    )

    result = reply(incoming)

    assert result["accepted"] is True
    assert result["sub_game_number"] == 0
    assert result["role"] == "thief"
