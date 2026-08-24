"""Refusing a counted series that cannot produce the evidence it owes (T057, ADR-013).

A counted game is not undoable. Only the FIRST meeting with an opponent counts, at most ten
count in total, and a report that cannot be assembled afterwards costs the points of a series
that was actually played -- possibly the opponent's too. So the cheapest place to discover a
missing declaration is before a game exists, not in the artifact after one.

Every check names the specific thing that is missing. "Not ready for counted play" sends
someone reading log lines at 2am; "no public MCP address is declared" sends them to the one
line they have to fill in.

A warm-up refuses none of this. That asymmetry is the point: local iteration must stay cheap,
and App. E rule 52 permits unlimited uncounted games precisely so that it can be.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from common.transport.kit_identity import GroupIdentity, IdentityError
from police_peer.evidence.git_revision import MissingGitRevisionError
from police_peer.evidence.identity_source import build_identity
from police_peer.evidence.token_ledger import TokenLedger


class CountedPlayNotReadyError(Exception):
    """A counted series was requested without the evidence a counted series owes."""


@dataclass(frozen=True, slots=True)
class CountedReadiness:
    """What a counted run resolved, once it is allowed to proceed."""

    identity: GroupIdentity
    config_digest: str


def assert_counted_ready(
    private,
    *,
    group_id: str,
    repo_root: Path | str,
    code_version: str,
    terms: dict,
    public_url: str = "",
    ledger: TokenLedger | None = None,
    group_code_confirmed: bool = False,
) -> CountedReadiness:
    """Resolve everything a counted series must declare, or refuse naming what is missing."""
    from common.transport.kit_identity import config_digest

    if not group_code_confirmed:
        raise CountedPlayNotReadyError(
            "the eight-character team code has not been confirmed against a human-approved "
            "team record (OPEN-003/OPEN-010). It appears in every submitted artifact, so a "
            "candidate value must not be played into one"
        )
    try:
        identity = build_identity(
            private, group_id=group_id, repo_root=repo_root, code_version=code_version,
            public_url=public_url,
        )
    except (IdentityError, MissingGitRevisionError) as exc:
        raise CountedPlayNotReadyError(f"the pre-game declaration is incomplete: {exc}") from exc

    if not terms:
        raise CountedPlayNotReadyError(
            "no negotiated terms, so no configuration digest can be computed and the two peers "
            "have nothing to prove they agreed on the same physics"
        )
    if ledger is not None and ledger.has_unknown_counted_usage():
        raise CountedPlayNotReadyError(
            "language-model usage is recorded as UNKNOWN for at least one counted step. The "
            "report declares total tokens consumed (App. E rule 54), and an unknown total "
            "cannot be declared honestly"
        )
    return CountedReadiness(identity=identity, config_digest=config_digest(terms))
