"""FastMCP client: one session, re-establish once, async-free facade.

``McpChannel`` is the *send* half of a peer and a drop-in ``PeerChannel``: the
series engine calls the same four ``send_*`` / four ``poll_*`` methods it calls
on the loopback transport and never learns a socket is involved.

The FastMCP client is async; the game loop is deliberately synchronous. So the
channel owns a private event loop on a daemon thread and drives every call
through ``run_coroutine_threadsafe(...).result(timeout)``. One session is held
across the whole series (FR-30); on a session-terminated error the channel tears
down and re-establishes **once** inside the original deadline, else it raises
``PeerUnreachableError`` (FR-31).

``poll_*`` never touch the network — they drain the local ``Inboxes`` that this
peer's own server fills as the opponent calls our tools.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import threading
import time
import urllib.error
import urllib.request

from common.transport.loopback import Inboxes


class PeerUnreachableError(Exception):
    """Raised when the opponent cannot be reached, even after one re-establish."""


class ProtocolRefusedError(Exception):
    """Raised when the MCP transport answered but the remote operation was refused."""

    def __init__(self, tool: str, response: object) -> None:
        self.tool = tool
        self.response = response
        super().__init__(f"peer refused {tool}: {response}")


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


class McpChannel:
    """A ``PeerChannel`` that reaches the opponent over FastMCP HTTP.

    ``payload``/``message`` asymmetry is applied at the call site: ``submit_audit``
    is invoked with a ``payload`` argument, the other three with ``message``.
    """

    def __init__(self, peer_url: str, inboxes: Inboxes, *, timeout: float = 30.0) -> None:
        self.peer_url = peer_url
        self.inboxes = inboxes
        self.timeout = timeout
        self._loop = asyncio.new_event_loop()
        self._loop_thread = threading.Thread(
            target=self._loop.run_forever, name="mcp-client-loop", daemon=True
        )
        self._loop_thread.start()
        self._client: object | None = None
        try:
            self._connect()
        except Exception:  # noqa: BLE001 — never leak the loop thread on a failed open
            self._stop_loop()
            raise

    # --- event-loop plumbing ----------------------------------------------------------------
    def _submit(self, coro, timeout: float | None = None):
        """Drive a coroutine on the private loop; cancel it if the wait times out.

        Cancelling the future stops the orphaned coroutine instead of leaving it
        running on the loop after the caller has moved on.
        """
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        try:
            return future.result(timeout=timeout if timeout is not None else self.timeout)
        except Exception:
            future.cancel()
            raise

    def _stop_loop(self) -> None:
        """Stop the private event loop and join its daemon thread. Idempotent."""
        if self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        self._loop_thread.join(timeout=5.0)

    def _connect(self, *, timeout: float | None = None) -> None:
        """Open (or reopen) the held session to the opponent."""
        from fastmcp import Client

        attempt_timeout = self.timeout if timeout is None else timeout
        client = Client(self.peer_url)
        try:
            self._submit(client.__aenter__(), timeout=attempt_timeout)
        except Exception:
            # A timed-out __aenter__ can own an HTTP session even though it never
            # reached the assignment below.  Close that attempt before retrying.
            with contextlib.suppress(Exception):
                self._submit(client.__aexit__(None, None, None), timeout=5.0)
            raise
        self._client = client

    def _teardown(self) -> None:
        if self._client is not None:
            with contextlib.suppress(Exception):
                self._submit(self._client.__aexit__(None, None, None), timeout=5.0)
            self._client = None

    # --- the one call path, with a single re-establish inside one deadline (FR-30/FR-31) ----
    def _call(self, tool: str, args: dict) -> dict:
        async def _invoke() -> dict:
            result = await self._client.call_tool(tool, args)
            return decoded_tool_result(result)

        def _refusal(value: object) -> bool:
            if not isinstance(value, dict):
                return False
            status = value.get("status") or value.get("result") or value.get("outcome")
            if isinstance(status, dict):
                return _refusal(status)
            if isinstance(status, str) and status.upper() in {
                "REFUSED", "REJECTED", "DENIED", "ERROR",
            }:
                return True
            return value.get("accepted") is False or value.get("ok") is False

        deadline = time.monotonic() + self.timeout
        try:
            response = self._submit(_invoke(), timeout=self.timeout)
            if _refusal(response):
                raise ProtocolRefusedError(tool, response)
            return response
        except ProtocolRefusedError:
            raise
        except Exception:  # noqa: BLE001 — re-establish once, within the same deadline
            # A turn/audit redelivered by the retry is absorbed by the at-least-once inbox
            # (FR-32/33/34), so a duplicate is safe even though delivery is not exactly-once.
            self._teardown()
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise PeerUnreachableError(
                    f"peer at {self.peer_url} timed out; no time to retry"
                ) from None
            try:
                time.sleep(min(0.5, max(0.0, remaining / 4)))
                self._connect()
                response = self._submit(_invoke(), timeout=max(0.1, deadline - time.monotonic()))
                if _refusal(response):
                    raise ProtocolRefusedError(tool, response)
                return response
            except ProtocolRefusedError:
                raise
            except PeerUnreachableError:
                raise
            except Exception as exc:  # noqa: BLE001
                raise PeerUnreachableError(
                    f"peer at {self.peer_url} unreachable after re-establish: {exc}"
                ) from exc

    def configure_peer_endpoints(
        self, *, police_url: str, thief_url: str, transition_timeout: float | None = None,
    ) -> None:
        """Install the opponent's role endpoints for the alternating series."""
        self._opponent_urls = {"police": police_url, "thief": thief_url}
        self._transition_timeout = transition_timeout or self.timeout

    def select_for_role(self, our_role) -> None:
        """Dial the complementary-role endpoint with closed, bounded retries.

        The opponent may be between sub-games while we switch endpoints.  Keep
        our background listener alive during that boundary instead of letting
        one slow MCP ``__aenter__`` consume the whole turn budget and terminate
        the counted runner.
        """
        role = getattr(our_role, "value", str(our_role))
        opponent_role = "thief" if role == "police" else "police"
        target = getattr(self, "_opponent_urls", {}).get(opponent_role)
        if not target or target == self.peer_url:
            return
        self._teardown()
        self.peer_url = target
        deadline = time.monotonic() + getattr(self, "_transition_timeout", self.timeout)
        delay = 0.5
        last_error: Exception | None = None
        while (remaining := deadline - time.monotonic()) > 0:
            try:
                self._connect(timeout=min(10.0, remaining))
                return
            except Exception as exc:  # noqa: BLE001 -- retry transient boundary failures
                last_error = exc
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                time.sleep(min(delay, remaining))
                delay = min(5.0, delay * 2.0)
        raise PeerUnreachableError(
            f"peer at {self.peer_url} did not accept an MCP session during role transition: "
            f"{last_error}"
        ) from last_error

    # --- outbound (PeerChannel) -------------------------------------------------------------
    def send_agreement(self, message: dict) -> dict:
        return self._call("negotiate", {"message": message})

    def send_turn(self, message: dict) -> dict:
        return self._call("receive_turn", {"message": message})

    def send_audit(self, payload: dict) -> dict:
        # Publish the exact reveal before making the symmetric outbound call so
        # a simultaneous inbound submit_audit can receive it in its tool result.
        self.inboxes.audit_reply = payload
        return self._call("submit_audit", {"payload": payload})

    def send_control(self, message: dict) -> dict:
        return self._call("receive_control", {"message": message})

    # --- inbound (PeerChannel): drain the local server's queues -----------------------------
    def poll_agreement(self) -> dict | None:
        return self.inboxes.agreements.popleft() if self.inboxes.agreements else None

    def poll_turn(self) -> dict | None:
        return self.inboxes.turns.popleft() if self.inboxes.turns else None

    def poll_audit(self) -> dict | None:
        return self.inboxes.audits.popleft() if self.inboxes.audits else None

    def poll_control(self) -> dict | None:
        return self.inboxes.controls.popleft() if self.inboxes.controls else None

    def close(self) -> None:
        """Tear down the session and stop the private loop. Idempotent."""
        self._teardown()
        self._stop_loop()


def edge_answers(url: str, timeout: float = 2.0) -> bool:
    """True once the peer MCP edge answers as live, False while it is still down.

    Health contract for the reference-v3 reserved ngrok domains:

    * plain browser-shaped GET -> ``406`` (an SSE probe -> ``400``): LIVE
    * ``502`` (or any 5xx): edge/tunnel answers, but the peer behind it has NOT
      started yet. Keep waiting; never treat it as connected.

    Only an HTTP answer below 500 proves the peer process is up (FR-9); a 5xx is
    the tunnel answering for a dead upstream.
    """
    try:
        with urllib.request.urlopen(urllib.request.Request(url, method="GET"), timeout=timeout):
            return True
    except urllib.error.HTTPError as exc:
        # 406/400 mean live; 502 means "our peers not started" -> keep waiting.
        return exc.code < 500
    except (urllib.error.URLError, OSError):
        return False
