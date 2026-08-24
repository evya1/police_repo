"""Counted play refuses BEFORE any game starts, one condition at a time (DEC-10, T057)."""

from __future__ import annotations

from pathlib import Path

import pytest

from common.config import PrivateConfig
from police_peer.evidence.identity_source import (
    CountedPlayRefusedError,
    assert_counted_ready,
)
from police_peer.evidence.token_ledger import TokenEvent, TokenLedger, UsageStatus
from police_peer.league.preflight import LeaguePairingGuard, PriorMatchRecord

COMMIT = "c" * 40
DIGEST = "d" * 64


def _repo(tmp_path: Path) -> Path:
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "HEAD").write_text(COMMIT + "\n", encoding="utf-8")
    return tmp_path


def _complete_private() -> PrivateConfig:
    return PrivateConfig(
        group_name="Team A",
        members=("Alice", "Bob"),
        repos={"cop": "https://github.com/a/cop", "thief": "https://github.com/a/thief"},
        mcp_servers={"cop": "https://cop.a.example/mcp", "thief": "https://thief.a.example/mcp"},
        llm_model="template",
        opponent_group_id="team-b",
    )


def _ready_kwargs(tmp_path: Path, **overrides) -> dict:
    kwargs = {
        "mode": "counted",
        "private": _complete_private(),
        "group_id": "team-a",
        "repo_root": _repo(tmp_path),
        "code_version": "1.00",
        "config_digest": DIGEST,
        "pairing_guard": LeaguePairingGuard(),
        "opponent_team": "team-b",
        "token_ledger": TokenLedger(),
        "signer_configured": True,
    }
    kwargs.update(overrides)
    return kwargs


def test_a_fully_ready_counted_run_does_not_refuse(tmp_path: Path) -> None:
    assert_counted_ready(**_ready_kwargs(tmp_path))  # must not raise


def test_warmup_never_refuses_on_any_condition(tmp_path: Path) -> None:
    """Every one of the seven checks below is skipped entirely in warm-up mode."""
    incomplete = {
        "mode": "warmup",
        "private": PrivateConfig(),  # nothing declared at all
        "group_id": "team-a",
        "repo_root": tmp_path,  # not even a git repo
        "code_version": "1.00",
        "config_digest": None,
        "pairing_guard": LeaguePairingGuard(),
        "opponent_team": None,
        "token_ledger": TokenLedger(),
        "signer_configured": False,
    }
    assert_counted_ready(**incomplete)  # must not raise


def test_refuses_when_config_digest_is_unavailable(tmp_path: Path) -> None:
    with pytest.raises(CountedPlayRefusedError, match="config digest"):
        assert_counted_ready(**_ready_kwargs(tmp_path, config_digest=None))


def test_refuses_when_identity_is_incomplete(tmp_path: Path) -> None:
    with pytest.raises(CountedPlayRefusedError, match="group_name"):
        assert_counted_ready(**_ready_kwargs(tmp_path, private=PrivateConfig()))


def test_refuses_when_the_git_commit_is_unavailable(tmp_path: Path) -> None:
    with pytest.raises(CountedPlayRefusedError, match="git"):
        assert_counted_ready(**_ready_kwargs(tmp_path, repo_root=tmp_path / "not-a-repo"))


def test_refuses_when_no_signer_is_configured(tmp_path: Path) -> None:
    with pytest.raises(CountedPlayRefusedError, match="signing credential"):
        assert_counted_ready(**_ready_kwargs(tmp_path, signer_configured=False))


def test_refuses_on_unknown_counted_token_usage(tmp_path: Path) -> None:
    ledger = TokenLedger()
    ledger.record(
        TokenEvent(
            sub_game_id="g1", step=1, counted=True, provider_called=True, fallback=False,
            status=UsageStatus.UNKNOWN, input_tokens=None, output_tokens=None,
        )
    )
    with pytest.raises(CountedPlayRefusedError, match="ineligible"):
        assert_counted_ready(**_ready_kwargs(tmp_path, token_ledger=ledger))


def test_refuses_when_the_opponent_is_not_yet_known(tmp_path: Path) -> None:
    with pytest.raises(CountedPlayRefusedError, match="opponent"):
        assert_counted_ready(**_ready_kwargs(tmp_path, opponent_team=None))


def test_refuses_on_a_repeat_counted_opponent(tmp_path: Path) -> None:
    guard = LeaguePairingGuard(
        prior_matches=[PriorMatchRecord(game_uid="g0", opponent_team="team-b")]
    )
    with pytest.raises(CountedPlayRefusedError):
        assert_counted_ready(**_ready_kwargs(tmp_path, pairing_guard=guard))


def test_refuses_past_the_maximum_counted_matches(tmp_path: Path) -> None:
    guard = LeaguePairingGuard(
        prior_matches=[
            PriorMatchRecord(game_uid=f"g{i}", opponent_team=f"opp-{i}") for i in range(10)
        ]
    )
    with pytest.raises(CountedPlayRefusedError):
        assert_counted_ready(**_ready_kwargs(tmp_path, pairing_guard=guard))
