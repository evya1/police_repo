"""Series-owned greeting context and lazy nonce regression tests."""

from common.transport.greetings import GreetingFactory, NegotiationContext, our_greeting

_TERMS = {
    "board_size": 7, "smell_grid_size": 5, "decay_per_step": 0.1,
    "emit_intensity": 0.9, "min_center_intensity": 0.5, "max_steps": 35,
    "barriers_max": 14, "setting": "Haifa", "hint_max_words": 15,
    "axis_origin_corner": "top-left", "axis_start_index": 0,
    "thief_start": [3, 3], "cop_start": [0, 0], "num_games": 6,
}


def _factory(calls: list[str]) -> GreetingFactory:
    def generate() -> str:
        nonce = f"nonce-{len(calls) + 1}"
        calls.append(nonce)
        return nonce

    context = NegotiationContext(
        terms=_TERMS, group_id="team-a", locks={"scent_model": "abc"},
        identity_block={"group_name": "Team A"},
    )
    return GreetingFactory(context, nonce_factory=generate)


def test_first_lookup_generates_exactly_one_nonce() -> None:
    calls: list[str] = []
    factory = _factory(calls)
    assert factory.nonce_for_sub_game(1) == "nonce-1"
    assert calls == ["nonce-1"]


def test_repeated_lookup_reuses_nonce_without_generating() -> None:
    calls: list[str] = []
    factory = _factory(calls)
    assert factory.nonce_for_sub_game(2) == factory.nonce_for_sub_game(2) == "nonce-1"
    assert calls == ["nonce-1"]


def test_different_sub_games_receive_independent_nonces() -> None:
    calls: list[str] = []
    factory = _factory(calls)
    assert factory.nonce_for_sub_game(2) == "nonce-1"
    assert factory.nonce_for_sub_game(3) == "nonce-2"
    assert calls == ["nonce-1", "nonce-2"]


def test_factory_preserves_existing_greeting_payload() -> None:
    calls: list[str] = []
    factory = _factory(calls)
    actual = factory.build(sub_game=2, role="police", opponent_group="team-b")
    expected = our_greeting(
        terms=_TERMS, nonce="nonce-1", group_id="team-a", role="police",
        sub_game_number=2, opponent_group="team-b", locks={"scent_model": "abc"},
        identity_block={"group_name": "Team A"},
    )
    assert actual == expected
