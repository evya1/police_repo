"""Synchronous ``PeerChannel`` facade over a lifecycle-owned async MCP session."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import cast

from common.transport.loopback import Inboxes
from common.transport.mcp_session import McpSession
from common.transport.mcp_session import PeerUnreachableError as PeerUnreachableError


class ProtocolRefusedError(Exception):
    """The peer answered but refused the remote operation."""

    def __init__(self, tool: str, response: object) -> None:
        self.tool = tool
        self.response = response
        super().__init__(f"peer refused {tool}: {response}")


def _fastmcp_client(url: str) -> object:
    """Construct the sole network client allowed by the shared-layer guard."""
    from fastmcp import Client

    return Client(url)


def decoded_tool_result(result: object) -> dict:
    """Return the peer's JSON verdict, including dicts encoded as MCP text."""
    data = getattr(result, "data", None)
    if isinstance(data, dict):
        return dict(data)
    for item in getattr(result, "content", ()):
        value = getattr(item, "text", None)
        if not isinstance(value, str):
            continue
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            continue
        if isinstance(decoded, dict):
            return decoded
    return {
        "status": "error",
        "accepted": False,
        "ok": False,
        "reason": "peer tool returned no JSON object verdict",
    }


def _is_refusal(value: object) -> bool:
    if not isinstance(value, dict):
        return False
    status = value.get("status") or value.get("result") or value.get("outcome")
    if isinstance(status, dict):
        return _is_refusal(status)
    if isinstance(status, str) and status.upper() in {
        "REFUSED", "REJECTED", "DENIED", "ERROR",
    }:
        return True
    return value.get("accepted") is False or value.get("ok") is False


class McpChannel:
    """Send through MCP and poll the local server-owned inboxes."""

    def __init__(self, peer_url: str, inboxes: Inboxes, *, timeout: float = 30.0) -> None:
        self.inboxes = inboxes
        self._session = McpSession(peer_url, timeout, _fastmcp_client)

    @property
    def peer_url(self) -> str:
        return self._session.peer_url

    @peer_url.setter
    def peer_url(self, value: str) -> None:
        self._session.peer_url = value

    @property
    def timeout(self) -> float:
        return self._session.timeout

    @timeout.setter
    def timeout(self, value: float) -> None:
        self._session.timeout = value

    def _call(self, tool: str, args: dict) -> dict:
        response = cast(
            dict,
            self._session.call_tool(tool, args, transform=decoded_tool_result),
        )
        if _is_refusal(response):
            raise ProtocolRefusedError(tool, response)
        return response

    def configure_peer_endpoints(
        self, *, police_url: str, thief_url: str, transition_timeout: float | None = None
    ) -> None:
        self._session.configure_endpoints(
            police_url=police_url,
            thief_url=thief_url,
            transition_timeout=transition_timeout,
        )

    def select_for_role(self, our_role) -> None:
        self._session.select_for_role(our_role)

    def send_agreement(self, message: dict) -> dict:
        return self._call("negotiate", {"message": message})

    def send_turn(self, message: dict) -> dict:
        return self._call("receive_turn", {"message": message})

    def send_audit(self, payload: dict) -> dict:
        self.inboxes.audit_reply = payload
        return self._call("submit_audit", {"payload": payload})

    def send_control(self, message: dict) -> dict:
        return self._call("receive_control", {"message": message})

    def poll_agreement(self) -> dict | None:
        return self.inboxes.agreements.popleft() if self.inboxes.agreements else None

    def poll_turn(self) -> dict | None:
        return self.inboxes.turns.popleft() if self.inboxes.turns else None

    def poll_audit(self) -> dict | None:
        return self.inboxes.audits.popleft() if self.inboxes.audits else None

    def poll_control(self) -> dict | None:
        return self.inboxes.controls.popleft() if self.inboxes.controls else None

    def close(self) -> None:
        self._session.close()


def edge_answers(url: str, timeout: float = 2.0) -> bool:
    """Return whether the peer process, rather than only its tunnel, answers."""
    try:
        with urllib.request.urlopen(urllib.request.Request(url, method="GET"), timeout=timeout):
            return True
    except urllib.error.HTTPError as exc:
        return exc.code < 500
    except (urllib.error.URLError, OSError):
        return False


def wait_for_edge(
    url: str,
    budget: float,
    *,
    probe: Callable[[str, float], bool] = edge_answers,
) -> bool:
    """Poll an MCP edge with bounded exponential backoff."""
    deadline = time.monotonic() + budget
    delay = 0.2
    while time.monotonic() < deadline:
        if probe(url, 0.5):
            return True
        time.sleep(delay)
        delay = min(2.0, delay * 1.5)
    return False
