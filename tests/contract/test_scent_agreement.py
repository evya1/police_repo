"""Contract: a declared scent-model mismatch is refused at the handshake boundary.

T005 acceptance criterion ``{#model_lock}`` and its final criterion: the selected
scent model is registered, hashed, and *declared for the handshake*, and a declared
mismatch "refuses start with a diagnostic and no partial game state, at the handshake
boundary — never inside the scent module. A peer that declares nothing is not a
mismatch and must still play."

This is a contract test, not a unit test, because it pins the *seam* between two
modules that must never be collapsed:

* the scent module (``police_peer.scent``) owns the pinned parameter document and its
  canonical hash (``model_lock_hash``) and states the start/refuse rule as data
  (``refusal_decision``) — but never refuses a handshake itself; and
* the transport handshake (``common.transport.negotiate.verify_greeting``) is the one
  place that turns a declared-model disagreement into a refusal (``SPAR-N05``).

The test declares the hash exactly the way a real peer would — by calling the scent
module's registry — so a drift in either the pinned document or the canonicalization
would break it, and asserts the handshake honors the scent module's own truth table
for every ours/theirs combination.
"""

from __future__ import annotations

import pytest

from common.transport.ids import terms_signature
from common.transport.negotiate import Agreed, verify_greeting
from common.transport.refusals import Refused
from police_peer.scent import (
    BOOK_MODEL,
    REFERENCE_MODEL,
    model_lock_hash,
    refusal_decision,
)

OUR_GROUP = "team-a"
THEIR_GROUP = "team-b"


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


def _greeting(terms: dict, *, scent_hash: str | None = None) -> dict:
    """A well-formed greeting that only varies in whether/what scent lock it declares."""
    nonce = "contract-nonce"
    greeting: dict = {
        "terms": terms,
        "nonce": nonce,
        "signature": terms_signature(terms, nonce),
        "group_id": THEIR_GROUP,
        "role": "thief",
        "sub_game_number": 1,
    }
    if scent_hash is not None:
        greeting["scent_model_sha256"] = scent_hash
    return greeting


class TestScentAgreementBoundary:
    """The declared scent model is agreed — or refused — at the handshake, not in scent."""

    def test_matching_declaration_starts_the_game(self) -> None:
        terms = _terms()
        our_hash = model_lock_hash(REFERENCE_MODEL)
        greeting = _greeting(terms, scent_hash=our_hash)
        result = verify_greeting(
            greeting, terms, OUR_GROUP, 1, our_locks={"scent_model": our_hash}
        )
        assert isinstance(result, Agreed)

    def test_mismatched_declaration_refuses_before_any_state(self) -> None:
        terms = _terms()
        greeting = _greeting(terms, scent_hash=model_lock_hash(BOOK_MODEL))
        with pytest.raises(Refused) as exc_info:
            verify_greeting(
                greeting,
                terms,
                OUR_GROUP,
                1,
                our_locks={"scent_model": model_lock_hash(REFERENCE_MODEL)},
            )
        # Refused carries an actionable diagnosis naming the family, at the boundary.
        assert exc_info.value.code == "SPAR-N05"
        assert "scent_model" in str(exc_info.value)
        # No Agreed value ever escaped — the refusal replaces the return, so there is
        # no partial game state to unwind.

    def test_opponent_declares_and_we_are_silent_still_plays(self) -> None:
        """A peer that declares nothing is not a mismatch (FR-16 / SPEC section 7)."""
        terms = _terms()
        greeting = _greeting(terms, scent_hash=model_lock_hash(BOOK_MODEL))
        result = verify_greeting(greeting, terms, OUR_GROUP, 1, our_locks=None)
        assert isinstance(result, Agreed)

    def test_we_declare_and_opponent_is_silent_still_plays(self) -> None:
        terms = _terms()
        greeting = _greeting(terms, scent_hash=None)
        result = verify_greeting(
            greeting,
            terms,
            OUR_GROUP,
            1,
            our_locks={"scent_model": model_lock_hash(REFERENCE_MODEL)},
        )
        assert isinstance(result, Agreed)

    def test_neither_declares_plays(self) -> None:
        terms = _terms()
        greeting = _greeting(terms, scent_hash=None)
        result = verify_greeting(greeting, terms, OUR_GROUP, 1)
        assert isinstance(result, Agreed)

    def test_declared_hash_is_the_registered_model_lock_hash(self) -> None:
        """The handshake compares the *registered* hash, and it is deterministic."""
        first = model_lock_hash(REFERENCE_MODEL)
        second = model_lock_hash(REFERENCE_MODEL)
        assert first == second  # same input document → same hash
        assert first != model_lock_hash(BOOK_MODEL)  # distinct registered models differ

    def test_boundary_honors_the_scent_module_truth_table(self) -> None:
        """For every ours/theirs combination the handshake agrees with the registry rule.

        The scent module states the decision as data (``refusal_decision``); the
        handshake must enforce exactly that and nothing wider.
        """
        ref = model_lock_hash(REFERENCE_MODEL)
        book = model_lock_hash(BOOK_MODEL)
        for ours in (ref, book, None):
            for theirs in (ref, book, None):
                terms = _terms()
                greeting = _greeting(terms, scent_hash=theirs)
                our_locks = {"scent_model": ours} if ours is not None else None
                expected = refusal_decision(ours, theirs)
                if expected == "refuse":
                    with pytest.raises(Refused) as exc_info:
                        verify_greeting(greeting, terms, OUR_GROUP, 1, our_locks=our_locks)
                    assert exc_info.value.code == "SPAR-N05"
                else:
                    result = verify_greeting(
                        greeting, terms, OUR_GROUP, 1, our_locks=our_locks
                    )
                    assert isinstance(result, Agreed)
