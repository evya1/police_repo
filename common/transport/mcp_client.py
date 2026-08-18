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
import threading
import urllib.error
import urllib.request

from common.transport.loopback import Inboxes


class PeerUnreachableError(Exception):
    """Raised when the opponent cannot be reached, even after one re-establish."""


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
        self._connect()

    # --- event-loop plumbing ----------------------------------------------------------------
    def _submit(self, coro, timeout: float | None = None):
        """Run a coroutine on the private loop and block for its result."""
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=timeout if timeout is not None else self.timeout)

    def _connect(self) -> None:
        """Open (or reopen) the held session to the opponent."""
        from fastmcp import Client

        client = Client(self.peer_url)
        self._submit(client.__aenter__(), timeout=self.timeout)
        self._client = client

    def _teardown(self) -> None:
        if self._client is not None:
            with contextlib.suppress(Exception):
                self._submit(self._client.__aexit__(None, None, None), timeout=5.0)
            self._client = None

    # --- the one call path, with a single re-establish (FR-30/FR-31) ------------------------
    def _call(self, tool: str, args: dict) -> dict:
        async def _invoke() -> dict:
            result = await self._client.call_tool(tool, args)
            return dict(result.data) if getattr(result, "data", None) is not None else {"ok": True}

        try:
            return self._submit(_invoke(), timeout=self.timeout)
        except Exception:  # noqa: BLE001 — one re-establish inside the deadline
            self._teardown()
            try:
                self._connect()
                return self._submit(_invoke(), timeout=self.timeout)
            except Exception as exc:  # noqa: BLE001
                raise PeerUnreachableError(
                    f"peer at {self.peer_url} unreachable after re-establish: {exc}"
                ) from exc

    # --- outbound (PeerChannel) -------------------------------------------------------------
    def send_agreement(self, message: dict) -> dict:
        return self._call("negotiate", {"message": message})

    def send_turn(self, message: dict) -> dict:
        return self._call("receive_turn", {"message": message})

    def send_audit(self, payload: dict) -> dict:
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
        self._loop.call_soon_threadsafe(self._loop.stop)


def edge_answers(url: str, timeout: float = 2.0) -> bool:
    """True once anything HTTP answers at the URL.

    ``406`` is the healthy answer for an MCP edge probed with a browser-shaped
    GET, but any status proves a listener is up (FR-9).
    """
    try:
        with urllib.request.urlopen(urllib.request.Request(url, method="GET"), timeout=timeout):
            return True
    except urllib.error.HTTPError:
        return True
    except (urllib.error.URLError, OSError):
        return False
