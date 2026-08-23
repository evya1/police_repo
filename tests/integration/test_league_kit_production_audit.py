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
        assert isinstance(audit["result_claim"], str), audit["result_claim"]
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


def test_internal_mode_audit_shape_is_unchanged() -> None:
    """The default lane must keep T046/T047 bytes exactly: internal `nonces` stays, and the
    kit's `sender` must not leak onto it."""
    ch_a, ch_b = pair("A", "B")
    sent = spy_audits(ch_a)
    run_pair_on(ch_a, ch_b, "A", "B")

    assert sent
    for audit in sent:
        assert set(audit) == {"records", "nonces", "result_claim"}, audit.keys()
        assert all("payload" not in r for r in audit["records"])
