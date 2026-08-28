"""Pure constructors for successful transport-tool responses."""

from __future__ import annotations

from collections.abc import Mapping


def accepted_audit_response(audit: Mapping[str, object]) -> dict[str, object]:
    """Build the accepted response from the local peer's published audit."""
    return {
        "status": "accepted",
        "accepted": True,
        "ok": True,
        "sender": audit["sender"],
        "records": audit["records"],
        "result_claim": audit["result_claim"],
    }
