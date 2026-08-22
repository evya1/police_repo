import pytest

from police_peer.league.preflight import (
    DuplicateOpponentError,
    FalseDeclarationError,
    InvalidModeError,
    LeaguePairingGuard,
    MaxMatchesExceededError,
    PriorMatchRecord,
)


def test_pairing_guard_warmup_always_allowed():
    guard = LeaguePairingGuard()
    # Warmup with any opponent and count is permitted
    assert guard.validate_pairing(opponent_team="team_x", mode="warmup", declared_prior_count=0)
    assert guard.validate_pairing(opponent_team="team_x", mode="warmup", declared_prior_count=99)


def test_pairing_guard_counted_match_progression():
    guard = LeaguePairingGuard()
    assert not guard.meets_submission_threshold()

    # Match 1: opponent A
    assert guard.validate_pairing(opponent_team="team_a", mode="counted", declared_prior_count=0)
    guard.record_match(PriorMatchRecord(game_uid="g1", opponent_team="team_a", mode="counted"))
    assert len(guard.get_distinct_opponents()) == 1
    assert not guard.meets_submission_threshold()

    # False declaration on match 2
    with pytest.raises(FalseDeclarationError):
        guard.validate_pairing(opponent_team="team_b", mode="counted", declared_prior_count=0)

    # Duplicate opponent A rejected
    with pytest.raises(DuplicateOpponentError):
        guard.validate_pairing(opponent_team="team_a", mode="counted", declared_prior_count=1)

    # Match 2: opponent B
    assert guard.validate_pairing(opponent_team="team_b", mode="counted", declared_prior_count=1)
    guard.record_match(PriorMatchRecord(game_uid="g2", opponent_team="team_b", mode="counted"))
    assert guard.meets_submission_threshold()


def test_pairing_guard_max_ten_counted_matches():
    guard = LeaguePairingGuard()
    for i in range(10):
        guard.record_match(
            PriorMatchRecord(game_uid=f"g{i}", opponent_team=f"team_{i}", mode="counted")
        )

    assert len(guard.get_counted_matches()) == 10

    # 11th counted match fails
    with pytest.raises(MaxMatchesExceededError):
        guard.validate_pairing(opponent_team="team_11", mode="counted", declared_prior_count=10)


def test_invalid_mode():
    guard = LeaguePairingGuard()
    with pytest.raises(InvalidModeError):
        guard.validate_pairing(opponent_team="team_a", mode="invalid_mode", declared_prior_count=0)
