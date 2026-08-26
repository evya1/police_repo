"""Reference-v3 audit compatibility at the final wire boundary."""

from common.transport.audit_wire import KitAuditWire


def test_survival_alias_normalizes_to_internal_survival() -> None:
    payload = {
        "sender": "thief",
        "records": [],
        "result_claim": {"outcome": "survival", "steps": 35},
    }

    normalized = KitAuditWire().inbound(payload)

    assert normalized["result_claim"] == "survival"
