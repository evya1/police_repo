"""Tests for negotiation: our_greeting — building the outgoing greeting.

FR-15: game_uid is derived, not exchanged — omitted on first contact, declared
once the opponent is known. FR-20: None fields (locks, uid) are omitted from the
wire dict. Verification order (FR-13/14/16) is covered in test_negotiate_verify.py.
"""

from __future__ import annotations

from common.transport.ids import game_uid, terms_signature
from common.transport.negotiate import our_greeting


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

    def test_identity_defaults_to_the_pre_existing_two_key_block(self) -> None:
        """Omitting identity_block reproduces the previous bytes exactly."""
        greeting = our_greeting(
            terms=self._terms(), nonce="n", group_id="a", role="police", sub_game_number=1,
        )
        assert greeting["identity"] == {"group_id": "a", "role": "police"}

    def test_identity_block_extends_without_displacing_group_id_or_role(self) -> None:
        """W2-P1: the extension is purely additive, and cannot be used to lie about who sent it."""
        greeting = our_greeting(
            terms=self._terms(), nonce="n", group_id="a", role="police", sub_game_number=1,
            identity_block={
                "group_id": "someone-else",  # an attempted override
                "role": "thief",  # an attempted override
                "group_name": "Team A",
                "llm_model": "template",
            },
        )
        assert greeting["identity"]["group_id"] == "a"
        assert greeting["identity"]["role"] == "police"
        assert greeting["identity"]["group_name"] == "Team A"
        assert greeting["identity"]["llm_model"] == "template"

    def test_identity_block_none_is_the_same_as_omitting_it(self) -> None:
        with_none = our_greeting(
            terms=self._terms(), nonce="n", group_id="a", role="police", sub_game_number=1,
            identity_block=None,
        )
        without = our_greeting(
            terms=self._terms(), nonce="n", group_id="a", role="police", sub_game_number=1,
        )
        assert with_none == without
