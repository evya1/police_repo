"""Counter-signed tool replies for peers that consume negotiation results directly."""

from __future__ import annotations

from collections.abc import Callable

from common.domain.scoring import Role, role_for
from common.transport.greetings import NegotiationContext, SeriesGreetingSession
from common.transport.ids import terms_signature


def _refused(reason: str) -> dict:
    return {"status": "refused", "accepted": False, "ok": False, "reason": reason}


def counter_signed_reply_builder(
    *,
    terms: dict,
    group_id: str,
    natural_role: Role,
    locks: dict[str, str] | None = None,
    identity_block: dict | None = None,
) -> Callable[[dict], dict]:
    """Build an idempotent rich reply for the optional direct-result interop lane."""
    greetings = SeriesGreetingSession(
        NegotiationContext(
            terms=terms,
            group_id=group_id,
            locks=locks,
            identity_block=identity_block,
        )
    )

    def reply(raw: dict) -> dict:
        theirs = raw.get("terms") if isinstance(raw, dict) else None
        nonce = raw.get("nonce") if isinstance(raw, dict) else None
        signature = raw.get("signature") if isinstance(raw, dict) else None
        sub_game = raw.get("sub_game_number") if isinstance(raw, dict) else None
        if not isinstance(sub_game, int) or not 0 <= sub_game <= 6:
            return _refused("sub_game_number must be an integer from 0 through 6")
        if theirs != terms:
            return _refused("terms do not match our configured 14-key contract")
        if not isinstance(nonce, str) or terms_signature(theirs, nonce) != signature:
            return _refused("incoming terms signature does not verify")

        if sub_game == 0:
            their_role = raw.get("role")
            if their_role not in {Role.POLICE.value, Role.THIEF.value}:
                return _refused("probe role must be police or thief")
            our_role = Role.THIEF if their_role == Role.POLICE.value else Role.POLICE
        else:
            our_role = role_for(natural_role, sub_game)
        if raw.get("role") == our_role.value:
            return _refused(f"role collision: both peers declared {our_role.value}")

        greeting = greetings.build(sub_game=sub_game, role=our_role.value)
        return {"status": "accepted", "accepted": True, "ok": True, **greeting}

    return reply
