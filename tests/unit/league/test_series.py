import pytest

from police_peer.league.series import (
    NUM_SUBGAMES,
    SeriesAggregator,
    SeriesError,
    SubGameOutcome,
    generate_role_schedule,
)


def test_generate_role_schedule():
    police_start = generate_role_schedule("police")
    assert len(police_start) == 6
    assert police_start == ["police", "thief", "police", "thief", "police", "thief"]

    thief_start = generate_role_schedule("thief")
    assert thief_start == ["thief", "police", "thief", "police", "thief", "police"]

    with pytest.raises(SeriesError):
        generate_role_schedule("invalid_role")


def test_series_aggregator_workflow():
    agg = SeriesAggregator(game_uid="series-abc", is_new_opponent=False)
    assert not agg.is_complete()

    # Incomplete finalize fails
    with pytest.raises(SeriesError, match="only 0/6"):
        agg.finalize_series()

    # Record 6 sub-games
    for i in range(NUM_SUBGAMES):
        sg = SubGameOutcome(
            sub_game_index=i,
            game_id=f"series-abc:{i}",
            role_for_this_sub_game="police" if i % 2 == 0 else "thief",
            outcome="capture",
            git_commit="commit123",
            tokens_used=1000,
        )
        agg.record_sub_game(sg)

    assert agg.is_complete()

    # Duplicate sub-game record fails
    with pytest.raises(SeriesError, match="already recorded"):
        agg.record_sub_game(
            SubGameOutcome(0, "series-abc:0", "police", "capture", "commit123")
        )

    score_res, evidence = agg.finalize_series()
    assert score_res.winner == "police"
    assert evidence["game_uid"] == "series-abc"
    assert evidence["total_llm_tokens_per_series"] == 6000
    assert len(evidence["sub_game_results"]) == 6
    assert len(evidence["sub_game_git_commits"]) == 6
    assert len(evidence["total_llm_tokens_per_sub_game"]) == 6
