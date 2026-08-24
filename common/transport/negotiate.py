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
    identity_block: dict | None = None,
) -> dict:
    """Build our outgoing negotiation greeting.

    Follows FR-20 omission convention: ``None`` fields are omitted from the
    wire dict (not emitted as null). The ``game_uid`` is omitted on the first
    sub-game (we don't yet know the opponent), and locks are omitted when not
    declared.

    ``identity_block`` is the greeting subset from
    :func:`common.transport.kit_identity.identity_greeting_block` and is purely
    ADDITIVE: it is merged into the existing ``identity`` key beside the
    ``group_id``/``role`` pair that has always been there, and omitting it
    reproduces the previous bytes exactly. ``verify_greeting`` never refuses on
    a missing, partial, or unknown identity field — an opponent that declares
    less than we do is not a fault (SPEC section 7).
    """
    locks = locks or {}
    # Derive the uid only when we know the opponent (sub-game 2 onward, or a
    # configured pairing). Omission never refuses (SPEC section 7.3).
    uid = (game_uid(terms, group_id, opponent_group)
           if opponent_group else None)

    # The handshake's own two identity keys stay first; a declared block extends them
    # without displacing either, so ``verify_greeting``'s group_id lookup is unchanged.
    identity: dict = {"group_id": group_id, "role": role}
    if identity_block:
        identity.update(identity_block)
        identity["group_id"], identity["role"] = group_id, role

    # FR-20: omit None fields — they are silence, not explicit nulls.
    greeting: dict = {
        "terms": terms,
        "nonce": nonce,
        "signature": terms_signature(terms, nonce),
        "group_id": group_id,
        "role": role,
        "sub_game_number": sub_game_number,
        "identity": identity,
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
                    sub_game_number: int,
                    our_locks: dict[str, str] | None = None) -> Agreed:
    """Check an inbound greeting, or refuse with a diagnosis.

    Verification runs in the fixed FR-13 order:

    1. **terms present** — the greeting must be a dict with a ``terms`` key
    2. **all 14 keys** — the terms must carry every key in :data:`TERMS_KEYS`
    3. **value-equality** — the terms must value-equal ours
    4. **signature re-verify** — re-hash with our own serializer and compare
    5. **locked-model comparison** — refuse only when both declare and disagree
    6. **pairing** — same ``sub_game_number``, complementary ``role``
    7. **declared ``game_uid``** — refuse only when both declare and disagree

    ``our_locks`` carries the hashes *we* have pinned, keyed by family name
    (``scent_model``, ``wire_shape``, ``info_mode``, ``smell_binding``). It is the
    only channel through which the handshake learns our declarations — the locked
    families themselves are role-specific and live outside the common layer, so
    without it step 5 has nothing of ours to compare and stays silent. Passing
    ``None`` (or omitting a family) means *we declare nothing* for it, which per
    SPEC section 7 can never refuse.
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
    #    Our hash comes from ``our_locks``; theirs rides beside the greeting under
    #    ``<family>_sha256``. Omission on either side is silence, never a refusal
    #    (SPEC section 7 truth table). This is the *only* place a locked-model
    #    disagreement is refused — the scent module supplies the pinned document and
    #    its hash, but never decides start/refuse; that decision belongs at the
    #    handshake boundary, here.
    declared = our_locks or {}
    for family, key in (
        ("scent_model", "scent_model_sha256"),
        ("wire_shape", "wire_shape_sha256"),
        ("info_mode", "info_mode_sha256"),
        ("smell_binding", "smell_binding_sha256"),
    ):
        ours_hash = declared.get(family)
        theirs_hash = raw.get(key)
        if ours_hash is not None and theirs_hash is not None and ours_hash != theirs_hash:
            raise Refused(
                "SPAR-N05",
                f"locked-model mismatch on {family}: we declared {ours_hash}, they "
                f"declared {theirs_hash}. Both sides pinned this family and the hashes "
                "differ, so a counted game cannot start. Refused at the handshake "
                "boundary before any game state exists.",
            )

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
