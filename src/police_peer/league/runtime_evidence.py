"""Production assembly of declaration evidence before a series can start."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from common.config import load_config
from common.transport.kit_identity import GroupIdentity, IdentityError, identity_greeting_block
from common.transport.terms import project_terms
from police_peer.evidence.git_revision import MissingGitRevisionError
from police_peer.evidence.identity_source import build_identity
from police_peer.evidence.token_ledger import TokenLedger
from police_peer.league.readiness import assert_counted_ready
from police_peer.wire.config import load_private


@dataclass(frozen=True, slots=True)
class RuntimeEvidence:
    identity: GroupIdentity | None
    token_ledger: TokenLedger

    @property
    def greeting_identity(self) -> dict | None:
        return identity_greeting_block(self.identity) if self.identity else None


def prepare_runtime_evidence(
    *, private_config: Path | str | None, shared_config: Path | str,
    group_id: str, mode: str, group_code_confirmed: bool, public_url: str,
    repo_root: Path | str, code_version: str,
) -> RuntimeEvidence:
    """Resolve honest runtime evidence; counted mode fails closed before transport starts."""
    private = load_private(private_config) if private_config else load_private("")
    shared = load_config(shared_config)
    terms = project_terms(shared, private.__dict__)
    terms["num_games"] = 6
    ledger = TokenLedger()
    if mode == "counted":
        ready = assert_counted_ready(
            private, group_id=group_id, repo_root=repo_root, code_version=code_version,
            terms=terms, public_url=public_url, ledger=ledger,
            group_code_confirmed=group_code_confirmed,
        )
        return RuntimeEvidence(ready.identity, ledger)
    if private_config:
        try:
            identity = build_identity(
                private, group_id=group_id, repo_root=repo_root, code_version=code_version,
                public_url=public_url,
            )
            return RuntimeEvidence(identity, ledger)
        except (IdentityError, MissingGitRevisionError):
            pass
    return RuntimeEvidence(None, ledger)
