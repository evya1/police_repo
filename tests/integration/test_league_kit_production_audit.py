"""Production-path `reference-v3` audit envelope (T054).

T052 built the kit wrap/unwrap helpers as pure functions and proved them with unit tests.
That is necessary and not sufficient: none of them had a production caller, so the runtime
audit stayed flat on the kit wire. Every test here inspects what production actually sent.
"""

from __future__ import annotations

from common.transport.loopback import pair
from tests.integration.kit_audit_harness import KIT_PROFILE, run_pair_on, spy_audits


def test_kit_mode_production_audit_is_nested_and_carries_role_sender() -> None:
    """Kit outbound top level is exactly `sender`/`records`/`result_claim`, each record
    nested around the *exact* original committed payload."""
    ch_a, ch_b = pair("A", "B")
    sent = spy_audits(ch_a)
    run_pair_on(ch_a, ch_b, "A", "B", wire_profile=KIT_PROFILE)

    assert sent, "production never sent an audit"
    for audit in sent:
        assert set(audit) == {"sender", "records", "result_claim"}, audit.keys()
        assert audit["sender"] in {"police", "thief"}, audit["sender"]
        assert set(audit["result_claim"]) == {"outcome", "steps"}
        assert audit["result_claim"]["outcome"] in {"capture", "escape"}
        assert type(audit["result_claim"]["steps"]) is int
        assert audit["result_claim"]["steps"] >= 0
        for record in audit["records"]:
            assert set(record) == {"payload", "nonce", "commit"}, record.keys()
            assert isinstance(record["payload"], dict)


def test_kit_mode_sender_is_the_role_not_the_group_id() -> None:
    """The kit's `AuditPayload.sender` is the producing side. A group ID there is the single
    most likely -- and silently accepted -- interop mistake."""
    ch_a, ch_b = pair("police-group-alpha", "B")
    sent = spy_audits(ch_a)
    run_pair_on(ch_a, ch_b, "police-group-alpha", "B", wire_profile=KIT_PROFILE)

    assert sent
    assert all(a["sender"] != "police-group-alpha" for a in sent)
    assert all(a["sender"] in {"police", "thief"} for a in sent)


def test_sender_is_present_at_both_levels_an_unconfigured_peer_sends() -> None:
    """`sender` must ride the default audit twice over, and both are load-bearing.

    1. The kit's ``AuditPayload`` declares ``sender`` a REQUIRED positional field, so a
       top-level audit without it makes the opponent raise
       ``TypeError: AuditPayload.__init__() missing 1 required positional argument:
       'sender'`` and stop answering — which reaches us as a turn timeout.
    2. Every sealed record carries its own ``sender`` INSIDE the committed payload
       (``turnseal.seal_turn``), so it is part of the commitment the opponent re-hashes;
       it cannot be edited on the wire without failing the audit.

    This runs with NO wire_profile, so it pins the default lane, not an opt-in one.
    """
    ch_a, ch_b = pair("A", "B")
    sent = spy_audits(ch_a)
    run_pair_on(ch_a, ch_b, "A", "B")

    assert sent, "production never sent an audit"
    for audit in sent:
        assert audit["sender"] in {"police", "thief"}, audit["sender"]
        for record in audit["records"]:
            assert record["payload"]["sender"] == audit["sender"], record["payload"]


def test_internal_mode_audit_shape_is_unchanged() -> None:
    """The `internal` lane must keep T046/T047 bytes exactly: internal `nonces` stays, and
    the kit's `sender` must not leak onto it.

    It is now the opt-in lane rather than the default, so it is named explicitly here — but
    its bytes are unchanged, which is the whole point of this test.
    """
    ch_a, ch_b = pair("A", "B")
    sent = spy_audits(ch_a)
    run_pair_on(ch_a, ch_b, "A", "B", wire_profile="internal")

    assert sent
    for audit in sent:
        assert set(audit) == {"records", "nonces", "result_claim"}, audit.keys()
        assert all("payload" not in r for r in audit["records"])
