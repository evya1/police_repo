"""MCP tool verdicts must be read from their actual JSON payload."""

from types import SimpleNamespace

from common.transport.mcp_client import decoded_tool_result


def test_text_encoded_refusal_is_not_replaced_with_success() -> None:
    result = SimpleNamespace(
        data=None,
        content=[SimpleNamespace(text='{"status":"refused","reason":"missing sender"}')],
    )

    assert decoded_tool_result(result) == {
        "status": "refused",
        "reason": "missing sender",
    }


def test_missing_json_verdict_fails_closed() -> None:
    result = SimpleNamespace(data=None, content=[SimpleNamespace(text="not json")])

    decoded = decoded_tool_result(result)

    assert decoded["ok"] is False
    assert decoded["accepted"] is False
