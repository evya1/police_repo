"""Assemble a real, verifiable :class:`GroupIdentity` and gate counted play on it (T057, ADR-013).

Nothing here defaults a required field to a placeholder (DEC-12): every missing piece raises a
distinctly-named error naming the missing item, so a counted refusal always says exactly what is
absent rather than "startup failed". Counted play refuses BEFORE any game starts -- every check
below is cheap and side-effect-free, and none of them is skipped because a game "already began".
"""

from __future__ import annotations

from pathlib import Path

from common.config import PrivateConfig
from common.transport.kit_identity import GroupIdentity, IdentityError
from police_peer.evidence.git_revision import MissingGitRevisionError, require_head_commit
from police_peer.evidence.runtime_summary import collect_runtime_summary
from police_peer.evidence.token_ledger import (
    CountedPlayIneligibleError,
    TokenLedger,
    assert_counted_eligible,
)
from police_peer.league.preflight import (
    LeagueEligibilityError,
    LeaguePairingGuard,
)


class IdentitySourceError(Exception):
    """A required piece of identity evidence is missing; nothing is substituted for it."""


class CountedPlayRefusedError(Exception):
    """Counted play refuses to start; the message names the specific missing item (DEC-10)."""


def build_identity(
    private: PrivateConfig,
    *,
    group_id: str,
    repo_root: Path,
    code_version: str,
    counted_games_played: int,
) -> GroupIdentity:
    """Assemble this group's declarable identity from private config and live evidence.

    ``counted_games_played`` is supplied by the caller (normally
    ``len(LeaguePairingGuard.get_counted_matches())``, exclusive of the series about to be
    played, per DEC-11) rather than recomputed here, so this function stays a pure projection
    of what it is given.
    """
    if not private.group_name:
        raise IdentitySourceError("private config is missing [game].group_name")
    if not private.members:
        raise IdentitySourceError("private config is missing [game].members")
    if not private.repos or {"cop", "thief"} - set(private.repos):
        raise IdentitySourceError(
            "private config is missing [game.repos].cop and/or [game.repos].thief"
        )
    if not private.mcp_servers or {"cop", "thief"} - set(private.mcp_servers):
        raise IdentitySourceError(
            "private config is missing [network.mcp_servers].cop and/or "
            "[network.mcp_servers].thief"
        )
    if not private.llm_model:
        raise IdentitySourceError("private config is missing [llm].model")

    try:
        commit = require_head_commit(repo_root)
    except MissingGitRevisionError as exc:
        raise IdentitySourceError(str(exc)) from exc

    hardware = collect_runtime_summary().as_dict()

    try:
        return GroupIdentity(
            group_id=group_id,
            group_name=private.group_name,
            members=private.members,
            repos=dict(private.repos),
            mcp_servers=dict(private.mcp_servers),
            llm_model=private.llm_model,
            hardware_spec=hardware,
            github_commit=commit,
            counted_games_played=counted_games_played,
            code_version=code_version,
        )
    except IdentityError as exc:
        raise IdentitySourceError(str(exc)) from exc


def assert_counted_ready(
    *,
    mode: str,
    private: PrivateConfig,
    group_id: str,
    repo_root: Path,
    code_version: str,
    config_digest: str | None,
    pairing_guard: LeaguePairingGuard,
    opponent_team: str | None,
    token_ledger: TokenLedger,
    signer_configured: bool,
) -> None:
    """Refuse BEFORE any game starts when counted play cannot honestly be reported.

    A warm-up (``mode != "counted"``) never refuses on any of these -- these are exactly the
    conditions under which a counted series would owe a report it could not produce or could
    not produce truthfully (DEC-10).
    """
    if mode != "counted":
        return

    if config_digest is None:
        raise CountedPlayRefusedError(
            "counted play refused: the negotiated terms' config digest could not be computed"
        )

    try:
        build_identity(
            private,
            group_id=group_id,
            repo_root=repo_root,
            code_version=code_version,
            counted_games_played=len(pairing_guard.get_counted_matches()),
        )
    except IdentitySourceError as exc:
        raise CountedPlayRefusedError(f"counted play refused: {exc}") from exc

    if not signer_configured:
        raise CountedPlayRefusedError(
            "counted play refused: no Step-0 signing credential is configured "
            "(INPUT-003: no course-supplied signing credential observed)"
        )

    try:
        assert_counted_eligible(token_ledger)
    except CountedPlayIneligibleError as exc:
        raise CountedPlayRefusedError(f"counted play refused: {exc}") from exc

    if opponent_team is None:
        raise CountedPlayRefusedError(
            "counted play refused: the opponent group is not yet known, so pairing "
            "eligibility cannot be checked"
        )
    try:
        pairing_guard.validate_pairing(
            opponent_team=opponent_team,
            mode="counted",
            declared_prior_count=len(pairing_guard.get_counted_matches()),
        )
    except LeagueEligibilityError as exc:
        raise CountedPlayRefusedError(f"counted play refused: {exc}") from exc
