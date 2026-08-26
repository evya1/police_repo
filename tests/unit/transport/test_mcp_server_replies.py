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


def test_audit_reply_returns_our_published_reveal_and_enqueues_theirs() -> None:
    inboxes = Inboxes()
    ours = {"sender": "thief", "records": [{"payload": {}, "nonce": "n", "commit": "c"}],
            "result_claim": {"outcome": "capture", "steps": 1}}
    theirs = {"sender": "police", "records": [],
              "result_claim": {"outcome": "capture", "steps": 1}}
    inboxes.audit_reply = ours

    assert _handle_audit(inboxes, theirs) == ours
    assert inboxes.audits.popleft() == theirs


def test_outbound_audit_is_published_before_network_call() -> None:
    channel = McpChannel.__new__(McpChannel)
    channel.inboxes = Inboxes()
    payload = {"sender": "thief", "records": [],
               "result_claim": {"outcome": "escape", "steps": 35}}

    def call(tool: str, args: dict) -> dict:
        assert channel.inboxes.audit_reply is payload
        assert tool == "submit_audit"
        assert args == {"payload": payload}
        return {"ok": True}

    channel._call = call
    assert channel.send_audit(payload) == {"ok": True}
