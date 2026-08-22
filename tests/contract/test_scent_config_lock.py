"""Contract: the production config path declares the selected scent model.

T005 wired the transport half of SPAR-N05, but nothing outside a test ever
computed a lock hash or placed it in PeerConfig, so a real peer greeted with no
declaration and verify_greeting read that silence as agreement. These tests pin
the config half: selection -> local hash -> greeting -> mismatch refusal.
"""

from __future__ import annotations

import pytest

from common.transport.negotiate import our_greeting, verify_greeting
from common.transport.refusals import Refused
from police_peer.scent.lock import model_lock_hash
from police_peer.sdk import create_peer
from police_peer.wire.config import PrivateConfig, load_private, peer_locks


def test_created_peer_declares_its_configured_scent_model() -> None:
    """The production factory must put the lock on the wire, not just support it.

    The transport half of SPAR-N05 has worked since T005, but nothing outside a
    test ever computed a lock hash or placed it in PeerConfig, so a real peer
    greeted with no declaration -- and verify_greeting reads silence as
    agreement. A counted game would start against a peer running different
    scent physics.
    """

    peer = create_peer("config/game.json", group_id="police-local")
    assert peer.config.locks is not None
    assert peer.config.locks["scent_model"] == model_lock_hash("subtractive_chebyshev_v1")

    greeting = our_greeting(
        group_id="police-local",
        role="police",
        terms=peer.config.terms,
        sub_game_number=1,
        nonce="a" * 32,
        locks=peer.config.locks,
    )
    assert greeting["scent_model_sha256"] == peer.config.locks["scent_model"]


def test_configured_peer_refuses_an_opponent_on_a_different_scent_model() -> None:
    """End-to-end on the production path: selection -> hash -> greeting -> refusal."""

    peer = create_peer("config/game.json", group_id="police-local")
    theirs = our_greeting(
        group_id="them",
        role="thief",
        terms=peer.config.terms,
        sub_game_number=1,
        nonce="b" * 32,
        locks=peer_locks(PrivateConfig(scent_model="multiplicative_book_v1")),
    )
    with pytest.raises(Refused) as excinfo:
        verify_greeting(
            theirs,
            our_terms=peer.config.terms,
            our_group_id="police-local",
            sub_game_number=1,
            our_locks=peer.config.locks,
        )
    assert "SPAR-N05" in str(excinfo.value)


def test_unknown_scent_model_in_private_config_is_refused(tmp_path) -> None:
    """A typo in game.toml must fail loudly, not silently pin an unknown hash."""
    from common.config import ConfigError

    toml = tmp_path / "game.toml"
    toml.write_text("scent_model = 'no_such_model'\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="unknown scent_model"):
        load_private(toml)
