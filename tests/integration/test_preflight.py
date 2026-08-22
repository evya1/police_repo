import pytest

from police_peer.league.preflight import (
    DuplicateOpponentError,
    LeaguePairingGuard,
    PriorMatchRecord,
)
from police_peer.reporting.schemas import (
    build_declaration,
    validate_schema,
)


def test_preflight_integration_with_signed_declarations():
    guard = LeaguePairingGuard()

    # Preflight check before match
    assert guard.validate_pairing(opponent_team="thief_group_9", mode="counted", declared_prior_count=0)

    # Build truthful preflight Declaration artifact
    declaration = build_declaration(
        game_uid="series-match-1",
        team="police_group_4",
        role="police",
        members=["agent1", "agent2"],
        police_repo_url="https://github.com/evya1/police_repo",
        thief_repo_url="https://github.com/opponent/thief_repo",
        mcp_addresses=["mcp://127.0.0.1:8000"],
        hardware="local-dev-box",
        model="qwen3-coder",
        token_budget=200000,
        start_time="2026-08-20T00:00:00Z",
        end_time="2026-08-20T01:00:00Z",
        num_games=6,
    )
    validate_schema(declaration)

    # Record completed match
    guard.record_match(
        PriorMatchRecord(
            game_uid="series-match-1",
            opponent_team="thief_group_9",
            mode="counted",
            signature="sig-hash-12345",
            extra_evidence={"declaration": declaration.as_dict()},
        )
    )

    # Next match against same opponent blocked
    with pytest.raises(DuplicateOpponentError):
        guard.validate_pairing(opponent_team="thief_group_9", mode="counted", declared_prior_count=1)

    # Warmup match against same opponent allowed
    assert guard.validate_pairing(opponent_team="thief_group_9", mode="warmup", declared_prior_count=1)
