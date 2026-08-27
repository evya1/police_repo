"""Series greeting ownership, idempotency, and alias-safety regressions."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from threading import Barrier, Event

import pytest

from common.domain.scoring import Role
from common.transport.greetings import (
    ConflictingGreetingError,
    NegotiationContext,
    SeriesGreetingSession,
    our_greeting,
)
from common.transport.negotiate import counter_signed_reply_builder

_TERMS = {
    "board_size": 7, "smell_grid_size": 5, "decay_per_step": 0.1,
    "emit_intensity": 0.9, "min_center_intensity": 0.5, "max_steps": 35,
    "barriers_max": 14, "setting": "Haifa", "hint_max_words": 15,
    "axis_origin_corner": "top-left", "axis_start_index": 0,
    "thief_start": [3, 3], "cop_start": [0, 0], "num_games": 6,
}


def _session(calls: list[str]) -> SeriesGreetingSession:
    def generate() -> str:
        nonce = f"nonce-{len(calls) + 1}"
        calls.append(nonce)
        return nonce

    context = NegotiationContext(
        terms=_TERMS, group_id="team-a", locks={"scent_model": "abc"},
        identity_block={"group_name": "Team A", "hardware": {"cpu": "test"}},
    )
    return SeriesGreetingSession(context, nonce_factory=generate)


def test_duplicate_request_returns_identical_complete_greeting_and_generates_once() -> None:
    calls: list[str] = []
    session = _session(calls)
    first = session.build(sub_game=2, role="police", opponent_group="team-b")
    second = session.build(sub_game=2, role="police", opponent_group="team-b")

    expected = our_greeting(
        terms=_TERMS, nonce="nonce-1", group_id="team-a", role="police",
        sub_game_number=2, opponent_group="team-b", locks={"scent_model": "abc"},
        identity_block={"group_name": "Team A", "hardware": {"cpu": "test"}},
    )
    assert first == second == expected
    assert calls == ["nonce-1"]


def test_distinct_sub_games_receive_independent_complete_greetings() -> None:
    calls: list[str] = []
    session = _session(calls)
    second = session.build(sub_game=2, role="police")
    third = session.build(sub_game=3, role="thief")

    assert second["nonce"] == "nonce-1"
    assert third["nonce"] == "nonce-2"
    assert second != third
    assert calls == ["nonce-1", "nonce-2"]


@pytest.mark.parametrize(("change", "value"), [
    ("role", "thief"),
    ("opponent_group", "team-c"),
])
def test_conflicting_same_subgame_specification_fails(change: str, value: str) -> None:
    session = _session([])
    request = {"sub_game": 2, "role": "police", "opponent_group": "team-b"}
    session.build(**request)
    request[change] = value

    with pytest.raises(ConflictingGreetingError, match="already established"):
        session.build(**request)


def test_original_mutable_inputs_cannot_change_series_context() -> None:
    terms = deepcopy(_TERMS)
    locks = {"scent_model": "stable"}
    identity = {"group_name": "Team A", "hardware": {"cpu": "stable"}}
    session = SeriesGreetingSession(
        NegotiationContext(terms, "team-a", locks, identity),
        nonce_factory=lambda: "nonce",
    )

    terms["thief_start"][0] = 99
    locks["scent_model"] = "changed"
    identity["hardware"]["cpu"] = "changed"
    greeting = session.build(sub_game=1, role="police")

    assert greeting["terms"]["thief_start"] == [3, 3]
    assert greeting["scent_model_sha256"] == "stable"
    assert greeting["identity"]["hardware"]["cpu"] == "stable"


def test_mutating_returned_greeting_cannot_change_cached_greeting() -> None:
    session = _session([])
    greeting = session.build(sub_game=2, role="police", opponent_group="team-b")
    greeting["terms"]["thief_start"][0] = 99
    greeting["identity"]["hardware"]["cpu"] = "changed"

    stable = session.build(sub_game=2, role="police", opponent_group="team-b")
    assert stable["terms"]["thief_start"] == [3, 3]
    assert stable["identity"]["hardware"]["cpu"] == "test"


def test_concurrent_same_subgame_build_is_atomic_and_generates_once() -> None:
    calls: list[str] = []
    workers_ready = Barrier(3)
    factory_entered = Event()
    release_factory = Event()

    def generate() -> str:
        calls.append("nonce")
        factory_entered.set()
        assert release_factory.wait(timeout=5)
        return "nonce"

    session = SeriesGreetingSession(
        NegotiationContext(deepcopy(_TERMS), "team-a"), nonce_factory=generate,
    )

    def build() -> dict:
        workers_ready.wait(timeout=5)
        return session.build(sub_game=2, role="police", opponent_group="team-b")

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(build) for _ in range(2)]
        workers_ready.wait(timeout=5)
        assert factory_entered.wait(timeout=5)
        release_factory.set()
        greetings = [future.result(timeout=5) for future in futures]

    assert greetings[0] == greetings[1]
    assert calls == ["nonce"]


def test_fresh_series_session_has_fresh_greeting_state() -> None:
    calls: list[str] = []
    first = _session(calls).build(sub_game=1, role="police")
    second = _session(calls).build(sub_game=1, role="police")

    assert first["nonce"] == "nonce-1"
    assert second["nonce"] == "nonce-2"
    assert first != second


def test_counter_signed_probe_cannot_rebind_one_nonce_to_another_role() -> None:
    terms = deepcopy(_TERMS)
    reply = counter_signed_reply_builder(
        terms=terms, group_id="ZeroOne0", natural_role=Role.THIEF,
    )
    police_probe = our_greeting(
        terms=terms, nonce="a" * 32, group_id="aviayeli",
        role="police", sub_game_number=0,
    )
    thief_probe = our_greeting(
        terms=terms, nonce="b" * 32, group_id="aviayeli",
        role="thief", sub_game_number=0,
    )
    assert reply(police_probe)["role"] == "thief"

    with pytest.raises(ConflictingGreetingError, match="already established"):
        reply(thief_probe)
