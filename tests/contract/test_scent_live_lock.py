"""Contract: selected scent profile lock wired through live greeting verification.

Tests that PeerConfig locks are passed to our_greeting() and verify_greeting(),
ensuring SPAR-N05 refusal fires on scent model hash mismatch during live handshake,
while backward compatibility (locks=None) is preserved.
"""

from __future__ import annotations

import pytest

from common.domain.scoring import Role
from common.transport.ids import terms_signature
from common.transport.negotiate import Agreed, our_greeting, verify_greeting
from common.transport.refusals import Refused
from common.transport.series import PeerConfig
from police_peer.scent.lock import model_lock_hash


class DummyBudgets:
    turn_timeout: float = 2.0
    connect_timeout: float = 2.0
    poll_interval: float = 0.005


def _terms() -> dict:
    return {
        "board_size": 7, "smell_grid_size": 5, "decay_per_step": 0.1,
        "emit_intensity": 0.9, "min_center_intensity": 0.5, "max_steps": 35,
        "barriers_max": 14, "setting": "New York", "hint_max_words": 15,
        "axis_origin_corner": "top-left", "axis_start_index": 0,
        "thief_start": [3, 3], "cop_start": [0, 0], "num_games": 6,
    }


def _opponent_greeting(
    terms: dict,
    *,
    group_id: str = "team-b",
    role: str = "thief",
    scent_hash: str | None = None,
) -> dict:
    nonce = "opponent-nonce-live"
    greeting: dict = {
        "terms": terms, "nonce": nonce,
        "signature": terms_signature(terms, nonce),
        "group_id": group_id, "role": role, "sub_game_number": 1,
    }
    if scent_hash is not None:
        greeting["scent_model_sha256"] = scent_hash
    return greeting


class TestScentLiveLockWiring:
    """Verify scent lock wiring through PeerConfig and greeting negotiation."""

    def test_our_greeting_includes_scent_model_hash_when_locked(self) -> None:
        terms = _terms()
        expected_hash = model_lock_hash("subtractive_chebyshev_v1")
        config = PeerConfig(
            natural_role=Role.POLICE,
            budgets=DummyBudgets(),
            terms=terms,
            locks={"scent_model": expected_hash},
        )
        greeting = our_greeting(
            terms=config.terms,
            nonce="test-nonce",
            group_id="team-a",
            role=config.natural_role.value,
            sub_game_number=1,
            locks=config.locks,
        )
        assert "scent_model_sha256" in greeting
        assert greeting["scent_model_sha256"] == expected_hash

    def test_verify_greeting_succeeds_when_opponent_declares_same_hash(self) -> None:
        terms = _terms()
        expected_hash = model_lock_hash("subtractive_chebyshev_v1")
        config = PeerConfig(
            natural_role=Role.POLICE,
            budgets=DummyBudgets(),
            terms=terms,
            locks={"scent_model": expected_hash},
        )
        opponent = _opponent_greeting(terms, scent_hash=expected_hash)
        result = verify_greeting(
            opponent,
            config.terms,
            "team-a",
            1,
            our_locks=config.locks,
        )
        assert isinstance(result, Agreed)

    def test_verify_greeting_raises_spar_n05_on_mismatched_hash(self) -> None:
        terms = _terms()
        expected_hash = model_lock_hash("subtractive_chebyshev_v1")
        different_hash = model_lock_hash("multiplicative_book_v1")
        config = PeerConfig(
            natural_role=Role.POLICE,
            budgets=DummyBudgets(),
            terms=terms,
            locks={"scent_model": expected_hash},
        )
        opponent = _opponent_greeting(terms, scent_hash=different_hash)
        with pytest.raises(Refused) as exc_info:
            verify_greeting(
                opponent,
                config.terms,
                "team-a",
                1,
                our_locks=config.locks,
            )
        assert exc_info.value.code == "SPAR-N05"
        assert "scent_model" in str(exc_info.value)

    def test_backward_compatibility_locks_none(self) -> None:
        terms = _terms()
        config = PeerConfig(
            natural_role=Role.POLICE,
            budgets=DummyBudgets(),
            terms=terms,
        )
        assert config.locks is None

        greeting = our_greeting(
            terms=config.terms,
            nonce="test-nonce",
            group_id="team-a",
            role=config.natural_role.value,
            sub_game_number=1,
            locks=config.locks,
        )
        assert "scent_model_sha256" not in greeting

        silent_opponent = _opponent_greeting(terms, scent_hash=None)
        result1 = verify_greeting(
            silent_opponent,
            config.terms,
            "team-a",
            1,
            our_locks=config.locks,
        )
        assert isinstance(result1, Agreed)

        declaring_opponent = _opponent_greeting(
            terms, scent_hash=model_lock_hash("subtractive_chebyshev_v1")
        )
        result2 = verify_greeting(
            declaring_opponent,
            config.terms,
            "team-a",
            1,
            our_locks=config.locks,
        )
        assert isinstance(result2, Agreed)
