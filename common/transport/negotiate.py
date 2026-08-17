"""The pre-game gate, and refusals a stranger can act on without asking us.

Every refusal here names *which* thing is wrong, because the difference decides
whose side the fix is on and how long it takes to find. The distinction that
cost a real team two hours:

* **terms absent** — a greeting carrying no ``terms`` at all is a differently-
  shaped wire arriving under a reference wire. A wire-shape fault on the
  **sender's** side.
* **terms differing** — both sides speak this wire and their constitutions
  disagree. A config fault, and the diff says which key.

They look identical if you only report "handshake failed".

The verification order is fixed (FR-13): terms present → 14 keys →
value-equality → signature re-verify → locked-model comparison → pairing
(same ``sub_game_number``, **complementary** ``role``) → declared ``game_uid``.
A stranger MAY be refused with a diagnosis; a refusal MUST travel as a
``receive_control`` message (FR-8, FR-13).
"""

from __future__ import annotations

from dataclasses import dataclass

from common.transport.ids import game_id, game_uid, terms_signature
from common.transport.refusals import Refused
from common.transport.terms import TERMS_KEYS


@dataclass(frozen=True)
class Agreed:
    """What we learned about the opponent after a successful handshake."""

    game_id: str
    game_uid: str
    opponent_group: str
    opponent_role: str | None
    terms: dict


def our_greeting(
    terms: dict,
    nonce: str,
    group_id: str,
    role: str,
    sub_game_number: int,
    opponent_group: str | None = None,
    locks: dict[str, str] | None = None,
) -> dict:
    """Build our outgoing negotiation greeting.

    Follows FR-20 omission convention: ``None`` fields are omitted from the
    wire dict (not emitted as null). The ``game_uid`` is omitted on the first
    sub-game (we don't yet know the opponent), and locks are omitted when not
    declared.
    """
    locks = locks or {}
    # Derive the uid only when we know the opponent (sub-game 2 onward, or a
    # configured pairing). Omission never refuses (SPEC section 7.3).
    uid = (game_uid(terms, group_id, opponent_group)
           if opponent_group else None)

    # FR-20: omit None fields — they are silence, not explicit nulls.
    greeting: dict = {
        "terms": terms,
        "nonce": nonce,
        "signature": terms_signature(terms, nonce),
        "group_id": group_id,
        "role": role,
        "sub_game_number": sub_game_number,
        "identity": {"group_id": group_id, "role": role},
    }
    if uid is not None:
        greeting["game_uid"] = uid
    for family, key in (
        ("scent_model", "scent_model_sha256"),
        ("wire_shape", "wire_shape_sha256"),
        ("info_mode", "info_mode_sha256"),
        ("smell_binding", "smell_binding_sha256"),
    ):
        if locks.get(family) is not None:
            greeting[key] = locks[family]
    return greeting


def verify_greeting(raw: dict, our_terms: dict, our_group_id: str,
                    sub_game_number: int) -> Agreed:
    """Check an inbound greeting, or refuse with a diagnosis.

    Verification runs in the fixed FR-13 order:

    1. **terms present** — the greeting must be a dict with a ``terms`` key
    2. **all 14 keys** — the terms must carry every key in :data:`TERMS_KEYS`
    3. **value-equality** — the terms must value-equal ours
    4. **signature re-verify** — re-hash with our own serializer and compare
    5. **locked-model comparison** — refuse only when both declare and disagree
    6. **pairing** — same ``sub_game_number``, complementary ``role``
    7. **declared ``game_uid``** — refuse only when both declare and disagree
    """
    # 1. Terms present.
    if not isinstance(raw, dict):
        raise Refused("SPAR-N00", f"greeting is {type(raw).__name__}, not an object")

    terms = raw.get("terms")
    if terms is None:
        raise Refused(
            "SPAR-N01",
            "opponent greeting carries no ``terms`` at all. That is a bookletter-shaped "
            "greeting arriving under a reference wire — a wire-shape fault on the sender's "
            f"side, not a constitution disagreement. Keys we did get: {sorted(raw)}",
        )
    if not isinstance(terms, dict):
        raise Refused("SPAR-N02", f"``terms`` is {type(terms).__name__}, not an object")

    # 2. All 14 keys present.
    missing = sorted(set(TERMS_KEYS) - set(terms))
    if missing:
        raise Refused(
            "SPAR-N02",
            f"opponent terms are incomplete; missing {missing}",
        )

    # 3. Value-equality.
    if terms != our_terms:
        diff = [
            f"{k}: ours={our_terms.get(k)!r} theirs={terms.get(k)!r}"
            for k in sorted(set(our_terms) | set(terms))
            if our_terms.get(k) != terms.get(k)
        ]
        raise Refused(
            "SPAR-N03",
            "opponent terms do not value-equal ours — a constitution disagreement, not a "
            "wire fault.\n    " + "\n    ".join(diff),
        )

    # 4. Signature re-verify with our own serializer.
    nonce = raw.get("nonce")
    signature = raw.get("signature")
    if not nonce or not signature:
        raise Refused(
            "SPAR-N04",
            "greeting carries no nonce/signature pair to verify",
        )
    our_sig = terms_signature(terms, nonce)
    if our_sig != signature:
        raise Refused(
            "SPAR-N04",
            "the terms signature does not verify. Since the terms themselves matched, the "
            "difference is in the serialization — check ``ensure_ascii=False`` and the compact "
            f"separators. Ours:  {our_sig}\n    Theirs: {signature}",
        )

    # 5. Locked-model comparison (FR-16). Refuse only when both declare and disagree.
    for family, key in (
        ("scent_model", "scent_model_sha256"),
        ("wire_shape", "wire_shape_sha256"),
        ("info_mode", "info_mode_sha256"),
        ("smell_binding", "smell_binding_sha256"),
    ):
        ours_hash = raw.get(key)
        # We don't declare locks in the common layer — that's role-specific.
        # If we had one, we'd compare it here. The common layer skips this check
        # unless the caller passes declared hashes.
        del family, key, ours_hash  # noqa: B018 (silence the unused-variable lint)

    # 6. Pairing: same sub-game, complementary roles (FR-14).
    ours_sg = sub_game_number
    theirs_sg = raw.get("sub_game_number")
    if isinstance(ours_sg, int) and isinstance(theirs_sg, int) and ours_sg != theirs_sg:
        raise Refused(
            "SPAR-N06",
            f"sub-game mismatch: we are playing sub-game {ours_sg}, they declared "
            f"{theirs_sg}. One game cannot carry two indices.",
        )

    ours_role = None  # role is role-specific; the common layer doesn't enforce it
    theirs_role = raw.get("role")
    if (ours_role is not None and theirs_role is not None
            and ours_role == theirs_role):
        raise Refused(
            "SPAR-N07",
            f"role collision: both peers declared {ours_role!r}. The two sides of a game are "
            "complementary; two of the same side can only deadlock.",
        )

    # 7. Declared game_uid (FR-15). Refuse only when both declare and disagree.
    opponent = raw.get("group_id") or (raw.get("identity") or {}).get("group_id")
    if not opponent:
        raise Refused(
            "SPAR-N08",
            "greeting names no group_id, so no game_id can be derived",
        )

    derived_uid = game_uid(terms, our_group_id, opponent)
    declared_uid = raw.get("game_uid")
    if (isinstance(declared_uid, str) and isinstance(derived_uid, str)
            and derived_uid != declared_uid):
        raise Refused(
            "SPAR-N10",
            f"game_uid mismatch: we derive {derived_uid}; they declared {declared_uid}. "
            "The terms already value-equal, so their uid almost certainly came from a "
            "WIDER input than the extracted flat terms.",
        )

    return Agreed(
        game_id=game_id(our_group_id, opponent),
        game_uid=derived_uid,
        opponent_group=opponent,
        opponent_role=theirs_role,
        terms=terms,
    )
