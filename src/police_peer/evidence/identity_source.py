"""Assemble the declarable identity from real sources, or refuse by name (T057, ADR-013).

Every value here comes from somewhere checkable: the private TOML the team filled in, the
host we are actually running on, the commit at HEAD, and our own pairing ledger. Nothing is
defaulted into existence. `GroupIdentity` does the refusing; this module's job is to gather
the inputs and to say which one is missing when it cannot.

The ledger deserves a note. `counted_games_played` is EXCLUSIVE of the series about to be
played, and it is a claim only we can make -- an opponent cannot verify it, which is exactly
why declaring it falsely is project-fatal under App. E rules 37-38 rather than merely wrong.
It is read from the pairing history that the league guard already maintains, so the number
comes from the same record that decides whether this pairing may be counted at all, rather
than from a second count that could drift from it.
"""

from __future__ import annotations

from pathlib import Path

from common.transport.kit_identity import GroupIdentity, IdentityError
from police_peer.evidence.git_revision import require_head_commit
from police_peer.evidence.runtime_summary import collect_runtime_summary
from police_peer.league.preflight import FilePairingHistoryStore

#: Both roles are declared by both peers (App. E rule 49), so both links are required.
REPO_ROLES = ("cop", "thief")


def counted_games_played(store: FilePairingHistoryStore | None = None) -> int:
    """How many counted series we have already played -- EXCLUSIVE of the one about to start."""
    records = (store or FilePairingHistoryStore()).load()
    return len(records)


def _endpoints(private, public_url: str) -> dict[str, str]:
    """Our two MCP endpoints. One public address serves both roles from this repository."""
    url = public_url or private.endpoints.public_url or private.endpoints.opponent_url
    if not url:
        raise IdentityError(
            "no public MCP address is declared. League play requires the server to be reachable "
            "from the public internet (App. E rule 10); set [network].public_url or pass "
            "--public-url once the tunnel is up"
        )
    return dict.fromkeys(REPO_ROLES, url)


def build_identity(
    private,
    *,
    group_id: str,
    repo_root: Path | str,
    code_version: str,
    public_url: str = "",
    history: FilePairingHistoryStore | None = None,
) -> GroupIdentity:
    """Gather every declarable value from a real source, or refuse by name."""
    identity = private.identity
    repos = dict(identity.repos)
    missing = sorted(set(REPO_ROLES) - set(repos))
    if missing:
        raise IdentityError(
            f"[game].repos must name both roles; missing {missing}. Both repository links are "
            f"declared by both peers and cross-linked in each README (App. E rules 49-50)"
        )
    return GroupIdentity(
        group_id=group_id or identity.group_id,
        group_name=identity.group_name,
        members=tuple(identity.members),
        repos=repos,
        mcp_servers=_endpoints(private, public_url),
        llm_model=private.llm.model,
        hardware_spec=collect_runtime_summary().as_dict(),
        github_commit=require_head_commit(repo_root),
        counted_games_played=counted_games_played(history),
        code_version=code_version,
    )
