"""Contract: selected scent profile lock wired through live greeting verification.

Tests that PeerConfig locks are passed to our_greeting() and verify_greeting(),
ensuring SPAR-N05 refusal fires on scent model hash mismatch during live handshake,
while backward compatibility (locks=None) is preserved.
"""

from __future__ import annotations

import pytest

from common.domain.scoring import Role
from common.transport.ids import terms_signature
from common.transport.loopback import pair
from common.transport.negotiate import Agreed, our_greeting, verify_greeting
from common.transport.refusals import Refused
from common.transport.series import PeerConfig, PeerFacade
from police_peer.scent.lock import model_lock_hash


class DummyBudgets:
    turn_timeout: float = 2.0
    connect_timeout: float = 2.0
    poll_interval: float = 0.005


class DummyEngine:
    def step(self, sub_game: int, role: Role) -> dict:
        return {"move": "STAY", "hint": "here"}


def _terms() -> dict:
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


def _opponent_greeting(
    terms: dict,
    *,
    group_id: str = "team-b",
    role: str = "thief",
    scent_hash: str | None = None,
) -> dict:
    nonce = "opponent-nonce-live"
    greeting: dict = {
        "terms": terms,
        "nonce": nonce,
        "signature": terms_signature(terms, nonce),
        "group_id": group_id,
        "role": role,
        "sub_game_number": 1,
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

        # Greeting has no scent_model_sha256
        greeting = our_greeting(
            terms=config.terms,
            nonce="test-nonce",
            group_id="team-a",
            role=config.natural_role.value,
            sub_game_number=1,
            locks=config.locks,
        )
        assert "scent_model_sha256" not in greeting

        # No refusal when opponent declares nothing
        silent_opponent = _opponent_greeting(terms, scent_hash=None)
        result1 = verify_greeting(
            silent_opponent,
            config.terms,
            "team-a",
            1,
            our_locks=config.locks,
        )
        assert isinstance(result1, Agreed)

        # No refusal when opponent declares a hash (we are silent)
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

    def test_live_peer_facade_exchange_greeting_with_matching_locks(self) -> None:
        chan_a, chan_b = pair()
        terms = _terms()
        scent_hash = model_lock_hash("subtractive_chebyshev_v1")
        config_a = PeerConfig(
            natural_role=Role.POLICE,
            budgets=DummyBudgets(),
            terms=terms,
            locks={"scent_model": scent_hash},
        )
        config_b = PeerConfig(
            natural_role=Role.THIEF,
            budgets=DummyBudgets(),
            terms=terms,
            locks={"scent_model": scent_hash},
        )
        facade_a = PeerFacade(chan_a, DummyEngine(), config_a, name="team-a")
        facade_b = PeerFacade(chan_b, DummyEngine(), config_b, name="team-b")

        import threading

        t_a = threading.Thread(target=facade_a._exchange_greeting)
        t_b = threading.Thread(target=facade_b._exchange_greeting)
        t_a.start()
        t_b.start()
        t_a.join(timeout=5)
        t_b.join(timeout=5)

        assert facade_a._game_id != ""
        assert facade_b._game_id != ""

    def test_live_peer_facade_exchange_greeting_with_mismatched_locks_refuses(self) -> None:
        chan_a, chan_b = pair()
        terms = _terms()
        hash_a = model_lock_hash("subtractive_chebyshev_v1")
        hash_b = model_lock_hash("multiplicative_book_v1")
        config_a = PeerConfig(
            natural_role=Role.POLICE,
            budgets=DummyBudgets(),
            terms=terms,
            locks={"scent_model": hash_a},
        )
        config_b = PeerConfig(
            natural_role=Role.THIEF,
            budgets=DummyBudgets(),
            terms=terms,
            locks={"scent_model": hash_b},
        )
        facade_a = PeerFacade(chan_a, DummyEngine(), config_a, name="team-a")
        facade_b = PeerFacade(chan_b, DummyEngine(), config_b, name="team-b")

        errors_a: list[Exception] = []
        errors_b: list[Exception] = []

        import threading

        def run_a() -> None:
            try:
                facade_a._exchange_greeting()
            except Exception as e:
                errors_a.append(e)

        def run_b() -> None:
            try:
                facade_b._exchange_greeting()
            except Exception as e:
                errors_b.append(e)

        t_a = threading.Thread(target=run_a)
        t_b = threading.Thread(target=run_b)
        t_a.start()
        t_b.start()
        t_a.join(timeout=5)
        t_b.join(timeout=5)

        assert len(errors_a) == 1
        assert isinstance(errors_a[0], Refused)
        assert errors_a[0].code == "SPAR-N05"
        assert len(errors_b) == 1
        assert isinstance(errors_b[0], Refused)
        assert errors_b[0].code == "SPAR-N05"
