"""Tests for negotiation: verify_greeting — fixed verification order.

FR-13: terms present → 14 keys → value-equality → signature re-verify →
locked-model comparison → pairing → declared uid. FR-14: omission never refuses
(missing role or sub_game_number is silence). FR-15: uid mismatch refused.
FR-16: locked-model refusal only when both declare and disagree.
"""

from __future__ import annotations

import pytest

from common.transport.ids import game_id, game_uid, terms_signature
from common.transport.negotiate import Agreed, verify_greeting
from common.transport.refusals import Refused


class TestVerifyGreeting:
    """Tests for verify_greeting — FR-13 fixed verification order."""

    def _valid_greeting(self, terms: dict, group_id: str = "team-b") -> dict:
        nonce = "test-nonce"
        return {
            "terms": terms,
            "nonce": nonce,
            "signature": terms_signature(terms, nonce),
            "group_id": group_id,
            "role": "thief",
            "sub_game_number": 1,
        }

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

    def test_accepts_valid_greeting(self) -> None:
        terms = self._terms()
        greeting = self._valid_greeting(terms)
        result = verify_greeting(greeting, terms, "team-a", 1)
        assert isinstance(result, Agreed)
        assert result.game_id == game_id("team-a", "team-b")
        assert result.opponent_group == "team-b"
        assert result.opponent_role == "thief"

    def test_refuses_non_dict(self) -> None:
        with pytest.raises(Refused) as exc_info:
            verify_greeting("not a dict", self._terms(), "team-a", 1)
        assert exc_info.value.code == "SPAR-N00"

    def test_refuses_missing_terms(self) -> None:
        with pytest.raises(Refused) as exc_info:
            verify_greeting({"nonce": "n", "signature": "s"}, self._terms(), "team-a", 1)
        assert exc_info.value.code == "SPAR-N01"

    def test_refuses_missing_keys(self) -> None:
        terms = self._terms()
        del terms["board_size"]
        greeting = self._valid_greeting(terms)
        with pytest.raises(Refused) as exc_info:
            verify_greeting(greeting, terms, "team-a", 1)
        assert exc_info.value.code == "SPAR-N02"

    def test_refuses_value_mismatch(self) -> None:
        terms = self._terms()
        theirs = {**terms, "board_size": 9}
        greeting = self._valid_greeting(theirs)
        with pytest.raises(Refused) as exc_info:
            verify_greeting(greeting, terms, "team-a", 1)
        assert exc_info.value.code == "SPAR-N03"

    def test_refuses_bad_signature(self) -> None:
        terms = self._terms()
        greeting = self._valid_greeting(terms)
        greeting["signature"] = "bad-signature"
        with pytest.raises(Refused) as exc_info:
            verify_greeting(greeting, terms, "team-a", 1)
        assert exc_info.value.code == "SPAR-N04"

    def test_refuses_missing_nonce(self) -> None:
        terms = self._terms()
        greeting = {"terms": terms, "signature": "sig", "group_id": "b"}
        with pytest.raises(Refused) as exc_info:
            verify_greeting(greeting, terms, "team-a", 1)
        assert exc_info.value.code == "SPAR-N04"

    def test_refuses_sub_game_mismatch(self) -> None:
        terms = self._terms()
        greeting = self._valid_greeting(terms)
        greeting["sub_game_number"] = 2
        with pytest.raises(Refused) as exc_info:
            verify_greeting(greeting, terms, "team-a", 1)
        assert exc_info.value.code == "SPAR-N06"

    def test_omitted_role_is_silence_not_refusal(self) -> None:
        """FR-14: missing role is silence, not a refusal."""
        terms = self._terms()
        greeting = self._valid_greeting(terms)
        del greeting["role"]
        result = verify_greeting(greeting, terms, "team-a", 1)
        assert isinstance(result, Agreed)
        assert result.opponent_role is None

    def test_derives_correct_uid(self) -> None:
        """game_uid is derived from terms + sorted group ids."""
        terms = self._terms()
        greeting = self._valid_greeting(terms)
        result = verify_greeting(greeting, terms, "team-a", 1)
        expected_uid = game_uid(terms, "team-a", "team-b")
        assert result.game_uid == expected_uid

    def test_refuses_uid_mismatch(self) -> None:
        """FR-15: declared uid that differs from derived uid is refused."""
        terms = self._terms()
        greeting = self._valid_greeting(terms)
        greeting["game_uid"] = "wrong-uid"
        with pytest.raises(Refused) as exc_info:
            verify_greeting(greeting, terms, "team-a", 1)
        assert exc_info.value.code == "SPAR-N10"

    def test_omitted_uid_is_tolerated(self) -> None:
        """FR-15: omitted game_uid is tolerated (sub-game 1 convention)."""
        terms = self._terms()
        greeting = self._valid_greeting(terms)
        greeting.pop("game_uid", None)  # safe delete
        result = verify_greeting(greeting, terms, "team-a", 1)
        assert isinstance(result, Agreed)

    def test_refuses_missing_group_id(self) -> None:
        terms = self._terms()
        greeting = self._valid_greeting(terms)
        del greeting["group_id"]
        with pytest.raises(Refused) as exc_info:
            verify_greeting(greeting, terms, "team-a", 1)
        assert exc_info.value.code == "SPAR-N08"

    def test_agreed_contains_all_fields(self) -> None:
        terms = self._terms()
        greeting = self._valid_greeting(terms)
        result = verify_greeting(greeting, terms, "team-a", 1)
        assert result.game_id == game_id("team-a", "team-b")
        assert result.opponent_group == "team-b"
        assert result.opponent_role == "thief"
        assert result.terms == terms
        assert isinstance(result.game_uid, str)
