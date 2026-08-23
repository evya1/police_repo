"""Signed Step-0 reproducibility declaration (T013, INPUT-003, ADR-010).

Step 0 is evidence, not authority: it never decides a move, verdict,
capture, or score. Every book-required fact (SEC-008, SEC-009, LEAGUE-007)
that is available at composition time is collected here; nothing is
fabricated, and no default signing credential is invented. Counted play with
a missing signer fails closed before the first move; template/no-provider
sparring may use the documented unsigned project profile.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from common.transport.canonical import canonical_bytes
from police_peer.evidence.runtime_summary import RuntimeSummary

Signer = Callable[[bytes], str]


class StepZeroError(Exception):
    """Base error for the Step-0 declaration boundary."""


class MissingCodeRevisionError(StepZeroError):
    """No verifiable code revision was supplied; counted play is blocked."""


class MissingConfigDigestError(StepZeroError):
    """No verifiable config digest was supplied; counted play is blocked."""


class MissingSigningCredentialError(StepZeroError):
    """Counted play requires an authorized signer and none was configured."""


@dataclass(frozen=True, slots=True)
class StepZeroDeclaration:
    """The unsigned facts of a Step-0 declaration for one sub-game attempt."""

    team: str
    role: str
    repo_url: str
    mcp_addresses: tuple[str, ...]
    runtime: RuntimeSummary
    llm_mode: str
    llm_model: str | None
    token_cap: int | None
    start_time: str
    game_id: str
    game_uid: str
    sub_game_number: int
    config_digest: str
    code_revision: str
    counted: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "kind": "step_zero_declaration",
            "team": self.team,
            "role": self.role,
            "repo_url": self.repo_url,
            "mcp_addresses": list(self.mcp_addresses),
            "runtime": self.runtime.as_dict(),
            "llm_mode": self.llm_mode,
            "llm_model": self.llm_model,
            "token_cap": self.token_cap,
            "start_time": self.start_time,
            "game_id": self.game_id,
            "game_uid": self.game_uid,
            "sub_game_number": self.sub_game_number,
            "config_digest": self.config_digest,
            "code_revision": self.code_revision,
            "counted": self.counted,
        }

    def canonical_bytes(self) -> bytes:
        return canonical_bytes(self.as_dict())


@dataclass(frozen=True, slots=True)
class SignedStepZero:
    """A Step-0 declaration plus its signature (or explicit unsigned status).

    ``signature`` is ``None`` only for the documented unsigned project
    profile (template/no-provider warmup with no signer configured); it is
    never ``None`` for ``declaration.counted is True``.
    """

    declaration: StepZeroDeclaration
    signer_key_id: str | None
    signature: str | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "declaration": self.declaration.as_dict(),
            "signer_key_id": self.signer_key_id,
            "signature": self.signature,
        }


def build_signed_step_zero(
    declaration: StepZeroDeclaration,
    *,
    signer: Signer | None,
    signer_key_id: str | None = None,
) -> SignedStepZero:
    """Sign ``declaration`` through an injected signer, failing closed for counted play.

    No default signing credential is ever fabricated (INPUT-003:
    ``NO_COURSE_CREDENTIAL_OBSERVED``). Missing or unverifiable
    ``code_revision``/``config_digest`` blocks counted play regardless of
    whether a signer is configured.
    """
    if declaration.counted:
        if not declaration.code_revision:
            raise MissingCodeRevisionError(
                "counted play requires a verifiable code_revision; none was supplied"
            )
        if not declaration.config_digest:
            raise MissingConfigDigestError(
                "counted play requires a verifiable config_digest; none was supplied"
            )
        if signer is None:
            raise MissingSigningCredentialError(
                "counted play requires an authorized Step-0 signer; none was configured "
                "(INPUT-003: no course-supplied signing credential observed) -- failing closed"
            )
        signature = signer(declaration.canonical_bytes())
        return SignedStepZero(
            declaration=declaration, signer_key_id=signer_key_id, signature=signature
        )

    # Template/no-provider sparring may use the documented unsigned project
    # profile, but still signs when a signer happens to be configured.
    if signer is None:
        return SignedStepZero(declaration=declaration, signer_key_id=None, signature=None)
    signature = signer(declaration.canonical_bytes())
    return SignedStepZero(
        declaration=declaration, signer_key_id=signer_key_id, signature=signature
    )


def verify_signed_step_zero(
    signed: SignedStepZero, *, verifier: Callable[[bytes, str], bool]
) -> bool:
    """Verify ``signed`` against its declaration's canonical bytes.

    An unsigned declaration (``signature is None``) never verifies as True;
    callers must check ``declaration.counted``/``signature is None``
    separately to decide whether an unsigned declaration is acceptable in
    context (only for uncounted/template sparring).
    """
    if signed.signature is None:
        return False
    return verifier(signed.declaration.canonical_bytes(), signed.signature)
