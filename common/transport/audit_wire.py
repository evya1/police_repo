"""The audit-wire port: how a settled sub-game's audit leaves and enters this peer (T054).

T052 built the kit wrap/unwrap conversions as pure functions and proved them in isolation.
They had no production caller, so the runtime kept sending flat internal records under an
internal top level even when speaking to the pinned kit. This module is the narrow seam
that makes the conversion a *runtime* choice: ``play_subgame`` asks the injected adapter to
shape what it sends and to normalize what it receives, and the composition root decides
which adapter that is.

Two implementations, one port:

* :class:`KitAuditWire` -- the ``reference-v3`` lane, and the DEFAULT
  (``DEFAULT_WIRE_PROFILE``). Top level is exactly ``sender`` / ``records`` /
  ``result_claim``; each record nests the *exact* payload that was already committed.
* :class:`IdentityAuditWire` -- the opt-in ``internal`` lane. Byte-for-byte what T046/T047
  already publish; the kit's ``sender`` never leaks onto it.

The default is the kit lane because the league IS the pinned kit: an opponent speaking
``reference-v3`` that receives a flat internal audit verifies zero records and settles
``tamper_forfeit``, which App. E rule 35 zeroes for BOTH teams. A wrong default that costs
both sides the game is worse than one that costs a sibling-vs-sibling run its wire shape,
and both siblings default the same way, so they still agree with each other.

Neither adapter hashes anything. Outbound wraps a payload that is already sealed, so there
is still exactly one commitment authority; inbound normalizes *before* the existing
verifier, which is left completely unchanged.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from common.transport.league_kit_envelope import unwrap_inbound_records, wrap_outbound_records
from common.transport.refusals import Refused


@runtime_checkable
class AuditWireAdapter(Protocol):
    """Shapes one settled sub-game's audit on the way out, and normalizes one on the way in."""

    def outbound(self, *, sender: str, audit: dict) -> dict:
        """Return the payload to hand to ``channel.send_audit``."""
        ...

    def inbound(self, payload: object) -> object:
        """Return the audit normalized to this project's internal flat shape."""
        ...


class IdentityAuditWire:
    """The internal lane: what we already produce is what we already verify."""

    __slots__ = ()

    def outbound(self, *, sender: str, audit: dict) -> dict:  # noqa: ARG002 - port shape
        """The internal audit travels unchanged; ``sender`` is a kit concern only."""
        return audit

    def inbound(self, payload: object) -> object:
        """An internal audit is already flat."""
        return payload


class KitAuditWire:
    """The ``reference-v3`` lane: the pinned kit's nested audit envelope."""

    __slots__ = ()

    def outbound(self, *, sender: str, audit: dict) -> dict:
        """Nest each already-committed record; declare the producing role as ``sender``.

        ``sender`` is the *role* that produced this audit (``police``/``thief``), never the
        group ID. The live kit requires ``result_claim`` to carry both the public outcome and
        the number of committed game steps; the internal ``nonces`` list does not cross.
        """
        outcome = audit["result_claim"]
        if outcome == "survival":
            outcome = "escape"
        return {
            "sender": sender,
            "records": wrap_outbound_records(list(audit["records"])),
            "result_claim": {"outcome": outcome, "steps": len(audit["records"]) - 1},
        }

    def inbound(self, payload: object) -> object:
        """Normalize a kit audit to the flat shape the existing verifier decodes strictly.

        Required-field absence or a wrong type is refused *here*, before any state mutates.
        Unknown extra top-level fields are tolerated: a peer that carries more than we know
        about is not thereby a faulty peer, and refusing one would be a self-inflicted
        interop failure.
        """
        if payload is None:
            return None
        if not isinstance(payload, dict):
            raise Refused(
                "SPAR-N12",
                f"kit audit is {type(payload).__name__}, not an object",
            )
        for key in ("sender", "records", "result_claim"):
            if key not in payload:
                raise Refused(
                    "SPAR-N12",
                    f"kit audit omits required top-level {key!r}; got {sorted(payload)}",
                )
        if not isinstance(payload["sender"], str):
            raise Refused("SPAR-N12", "kit audit 'sender' must be the producing role string")
        claim = payload["result_claim"]
        if isinstance(claim, dict):
            outcome = claim.get("outcome")
            steps = claim.get("steps")
            if outcome not in {"capture", "escape", "survival"}:
                raise Refused(
                    "SPAR-N12",
                    "kit audit 'result_claim.outcome' must be capture, escape, or survival",
                )
            if type(steps) is not int or steps < 0:
                raise Refused("SPAR-N12", "kit audit 'result_claim.steps' must be a non-negative int")
            claim = "survival" if outcome in {"escape", "survival"} else outcome
        elif not isinstance(claim, str):
            raise Refused("SPAR-N12", "kit audit 'result_claim' must be an object")
        if not isinstance(payload["records"], list):
            raise Refused("SPAR-N12", "kit audit 'records' must be a list")
        return dict(payload, records=unwrap_inbound_records(payload["records"]), result_claim=claim)


#: Wire profile name -> adapter. The composition root resolves one of these once.
AUDIT_WIRE_PROFILES: dict[str, AuditWireAdapter] = {
    "internal": IdentityAuditWire(),
    "reference-v3": KitAuditWire(),
}

#: The lane an unconfigured peer speaks. ONE default, named here and nowhere else, so the
#: composition root and any direct ``play_subgame`` caller cannot drift apart.
DEFAULT_WIRE_PROFILE = "reference-v3"


def default_audit_wire() -> AuditWireAdapter:
    """The adapter an unconfigured caller gets. Never inline ``IdentityAuditWire()``."""
    return AUDIT_WIRE_PROFILES[DEFAULT_WIRE_PROFILE]


def resolve_audit_wire(profile: str | None) -> AuditWireAdapter:
    """Resolve a configured wire profile, or refuse an unknown one at startup.

    Failing here -- at composition, before a game exists -- is the whole point: an
    unrecognized profile that silently fell back to some other lane would look like a
    working peer and produce an unreadable audit for the opponent.
    """
    if profile is None:
        return default_audit_wire()
    try:
        return AUDIT_WIRE_PROFILES[profile]
    except KeyError:
        raise ValueError(
            f"unknown wire profile {profile!r}; known: {sorted(AUDIT_WIRE_PROFILES)}"
        ) from None
