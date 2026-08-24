"""Group identity: what a declaration states, and what rides the greeting (CT-08, ADR-013).

The declaration is the one place everything fixed across a series is written down -- who we
are, which repositories hold our code, which endpoints we serve, what machine we ran on, which
model we used, and which commit actually played. Book ch.5's step-zero and App. E rules 24 and
53 both land here.

Two rules shape the whole module:

**Nothing is invented.** Every field is required explicitly and a missing one raises by name.
An identity assembled from placeholders would be a false declaration under App. E rules 37-38,
and it would look exactly like a true one.

**The signature is sign-then-insert.** The per-group digest covers the block as it stood
BEFORE the signature key existed, so the field is excluded from its own preimage. It carries a
``sha256:`` prefix; the consensus digest in ``kit_consensus`` does not. They are different
fields computed over different things, and giving them the same shape would invite exactly one
confusion too many.

The greeting carries a SUBSET: enough for an opponent to write our half of their declaration,
and nothing they cannot check. Hardware travels as a digest, never as a spec -- they cannot
verify our RAM, and a value nobody can check does not belong on a wire.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field

from common.transport.canonical import canonical_bytes

#: Sign-then-insert prefix for the per-group declaration signature.
SIGNATURE_PREFIX = "sha256:"

_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")

#: The keys that ride the greeting. Everything an opponent needs to name us truthfully in
#: their own declaration, and nothing they would have to take on trust.
GREETING_KEYS = (
    "group_id", "group_name", "repos", "mcp_servers", "llm_model",
    "hardware_spec_sha256", "github_commit", "counted_games_played", "code_version",
)


class IdentityError(Exception):
    """An identity is incomplete or malformed, and will not be guessed at."""


@dataclass(frozen=True, slots=True)
class GroupIdentity:
    """One group's fixed, declarable identity for a series."""

    group_id: str
    group_name: str
    members: tuple[str, ...]
    repos: dict[str, str]
    mcp_servers: dict[str, str]
    llm_model: str
    hardware_spec: dict
    github_commit: str
    counted_games_played: int
    code_version: str
    extra: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("group_id", "group_name", "llm_model", "code_version"):
            if not getattr(self, name):
                raise IdentityError(f"{name} is required and was not supplied")
        if not self.members:
            raise IdentityError("members is required: a declaration names its group's members")
        for name in ("repos", "mcp_servers"):
            block = getattr(self, name)
            missing = sorted({"cop", "thief"} - set(block))
            if missing:
                raise IdentityError(
                    f"{name} must name both roles; missing {missing}. Both repositories are "
                    f"declared by both peers (App. E rule 49)"
                )
        if not self.hardware_spec:
            raise IdentityError(
                "hardware_spec is required: the computational-fairness declaration is what "
                "earns the normalization bonus (book ch.5)"
            )
        if not _COMMIT_RE.match(self.github_commit):
            raise IdentityError(
                f"github_commit must be a 40-character hex sha, got {self.github_commit!r}. "
                f"Every counted game records the exact commit that played (App. E rule 53)"
            )
        if self.counted_games_played < 0:
            raise IdentityError("counted_games_played cannot be negative")


def hardware_digest(spec: dict) -> str:
    """Canonical digest of a hardware spec -- what travels when the spec itself does not."""
    return hashlib.sha256(canonical_bytes(spec)).hexdigest()


def config_digest(terms: dict) -> str:
    """Canonical digest of the negotiated terms; the shared configuration's identifier."""
    return hashlib.sha256(canonical_bytes(terms)).hexdigest()


def _unsigned_block(identity: GroupIdentity) -> dict:
    return {
        "group_id": identity.group_id,
        "group_name": identity.group_name,
        "members": list(identity.members),
        "repos": dict(identity.repos),
        "mcp_servers": dict(identity.mcp_servers),
        "llm_model": identity.llm_model,
        "hardware_spec": dict(identity.hardware_spec),
        "hardware_spec_sha256": hardware_digest(identity.hardware_spec),
        "github_commit": identity.github_commit,
        "counted_games_played": identity.counted_games_played,
        "code_version": identity.code_version,
        **identity.extra,
    }


def group_block(identity: GroupIdentity) -> dict:
    """The declaration's block for one group, signed then sealed."""
    block = _unsigned_block(identity)
    return {**block, "signature": SIGNATURE_PREFIX + hashlib.sha256(
        canonical_bytes(block)
    ).hexdigest()}


def verify_group_block(block: dict) -> bool:
    """Re-derive the signature over the block minus the signature itself."""
    declared = block.get("signature")
    if not isinstance(declared, str) or not declared.startswith(SIGNATURE_PREFIX):
        return False
    unsigned = {k: v for k, v in block.items() if k != "signature"}
    expected = SIGNATURE_PREFIX + hashlib.sha256(canonical_bytes(unsigned)).hexdigest()
    return declared == expected


def identity_greeting_block(identity: GroupIdentity) -> dict:
    """The subset that rides the greeting. Hardware travels as a digest, never as a spec."""
    block = _unsigned_block(identity)
    return {k: block[k] for k in GREETING_KEYS}


def identity_from_greeting(raw: dict) -> dict | None:
    """Read an opponent's declared identity, tolerantly.

    Unknown keys are kept and missing ones are simply absent: SPEC section 7's stance is to
    refuse only when both sides declare and disagree, so an opponent that says less than we do
    is not a fault. Returns None when nothing identity-shaped was declared at all.
    """
    block = raw.get("identity")
    if not isinstance(block, dict):
        return None
    known = {k: v for k, v in block.items() if k in GREETING_KEYS}
    return known or None
