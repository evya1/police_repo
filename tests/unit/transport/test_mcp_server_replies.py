from copy import deepcopy

import pytest

from common.transport.loopback import Inboxes
from common.transport.mcp_client import McpChannel
from common.transport.mcp_server import _handle_audit, _handle_negotiate


def test_probe_is_countersigned_without_entering_series_inbox() -> None:
    inboxes = Inboxes()
    inboxes.agreement_reply = lambda message: {
        "ok": True, "accepted": True, "sub_game_number": message["sub_game_number"],
    }

    response = _handle_negotiate(inboxes, {"sub_game_number": 0})

    assert response["accepted"] is True
    assert not inboxes.agreements


@pytest.mark.parametrize("sender", ["police", "thief"])
def test_audit_reply_returns_accepted_local_audit_and_enqueues_theirs(sender: str) -> None:
    inboxes = Inboxes()
    local_audit = {
        "sender": sender,
        "records": [{"payload": {}, "nonce": "n", "commit": "c"}],
        "result_claim": {"outcome": "capture", "steps": 1},
        "status": "must-not-override",
        "accepted": False,
        "ok": False,
        "private_note": "must-not-leak",
    }
    opponent_audit = {
        "sender": "thief" if sender == "police" else "police",
        "records": [],
        "result_claim": {"outcome": "capture", "steps": 1},
    }
    local_before = deepcopy(local_audit)
    opponent_before = deepcopy(opponent_audit)
    inboxes.audit_reply = local_audit

    response = _handle_audit(inboxes, opponent_audit)

    expected = {
        "status": "accepted",
        "accepted": True,
        "ok": True,
        "sender": local_audit["sender"],
        "records": local_audit["records"],
        "result_claim": local_audit["result_claim"],
    }
    assert response == expected
    assert set(response) == {
        "status",
        "accepted",
        "ok",
        "sender",
        "records",
        "result_claim",
    }
    assert response is not local_audit
    assert local_audit == local_before
    assert opponent_audit == opponent_before
    assert list(inboxes.audits) == [opponent_audit]
    assert inboxes.audits[0] is opponent_audit


def test_audit_before_local_publication_uses_acknowledgment_fallback() -> None:
    """A pre-publication call is enqueued but cannot return or invent our audit."""
    inboxes = Inboxes()
    opponent_audit = {
        "sender": "police",
        "records": [{"payload": {"step": 1}}],
        "result_claim": {"outcome": "escape", "steps": 35},
    }
    opponent_before = deepcopy(opponent_audit)

    response = _handle_audit(inboxes, opponent_audit)

    assert response == {"ok": True}
    assert opponent_audit == opponent_before
    assert list(inboxes.audits) == [opponent_audit]
    assert inboxes.audits[0] is opponent_audit


def test_outbound_audit_is_published_before_network_call() -> None:
    channel = McpChannel.__new__(McpChannel)
    channel.inboxes = Inboxes()
    payload = {
        "sender": "thief",
        "records": [],
        "result_claim": {"outcome": "escape", "steps": 35},
    }

    def call(tool: str, args: dict) -> dict:
        assert channel.inboxes.audit_reply is payload
        assert tool == "submit_audit"
        assert args == {"payload": payload}
        return {"ok": True}

    channel._call = call
    assert channel.send_audit(payload) == {"ok": True}
