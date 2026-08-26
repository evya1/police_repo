"""FastMCP server: four tools, lazy import, no blocking in handlers.

The server is the *receive* half of a peer. Each tool validates its argument,
enqueues it into the peer's own ``Inboxes``, and returns ``{"ok": True}`` at
once — it never awaits game progress, mutates game state, or touches crypto
(FR-8). Two peers each awaiting the other inside a handler would deadlock
instantly, so handlers do exactly three things: accept, enqueue, return.

``fastmcp`` is imported lazily inside ``build_server`` so the zero-dependency
loopback spine keeps running with nothing installed (NFR-5, FR-39).
"""

from __future__ import annotations

import socket
import threading
import time
import urllib.error
import urllib.request
from typing import Any

from common.transport.loopback import Inboxes

# The exact tool names the wire surface exposes (FR-6/7). The argument-name
# asymmetry is load-bearing: ``submit_audit`` takes ``payload``; the other three
# take ``message`` (TC-02).
TOOL_NAMES = ("negotiate", "receive_turn", "submit_audit", "receive_control")


def build_server(inboxes: Inboxes, *, name: str = "peer") -> Any:
    """Construct the FastMCP app with the four tools bound to ``inboxes``.

    ``fastmcp`` is imported here, never at module scope, so importing this module
    does not require the dependency and the boundary stays provable.
    """
    from fastmcp import FastMCP

    mcp = FastMCP(name=name)

    @mcp.tool
    def negotiate(message: dict) -> dict:
        """Accept a negotiation greeting / signed terms and enqueue it."""
        inboxes.agreements.append(message)
        reply = getattr(inboxes, "agreement_reply", None)
        if reply is not None:
            return reply(message)
        return {"ok": True}

    @mcp.tool
    def receive_turn(message: dict) -> dict:
        """Accept a turn message and enqueue it."""
        inboxes.turns.append(message)
        return {"ok": True}

    @mcp.tool
    def submit_audit(payload: dict) -> dict:
        """Accept an end-of-game audit reveal and enqueue it. Note: ``payload``."""
        inboxes.audits.append(payload)
        return {"ok": True}

    @mcp.tool
    def receive_control(message: dict) -> dict:
        """Accept a control signal (enable / status / restart / quit) and enqueue it."""
        inboxes.controls.append(message)
        return {"ok": True}

    return mcp


def port_is_held(host: str, port: int) -> bool:
    """A connect probe, never a trial bind (FR-37).

    Racing the real server for the address with a trial ``bind`` opens a window
    where the port looks free but is taken a millisecond later. A ``connect``
    probe asks the only question that matters: is something answering here now?
    """
    with socket.socket() as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, port)) == 0


def preflight(inboxes: Inboxes) -> bool:
    """Run the shared-layer guard scan; refuse to start on violation (FR-39).

    The one invariant this peer can check locally before binding a port is that
    it actually has the four queues a handler needs. A structural violation here
    means the caller wired the server wrong, and a server that cannot enqueue
    must never accept a connection.
    """
    required = ("agreements", "turns", "audits", "controls")
    return all(hasattr(inboxes, q) for q in required)


class ServerHandle:
    """A running server on a daemon thread, plus the URL it answers on."""

    def __init__(self, url: str, thread: threading.Thread) -> None:
        self.url = url
        self.thread = thread


def serve_background(
    inboxes: Inboxes,
    *,
    host: str = "127.0.0.1",
    port: int,
    name: str = "peer",
    ready_timeout: float = 15.0,
) -> ServerHandle:
    """Preflight, then run the server on a daemon thread and wait until it answers.

    The server never binds if preflight refuses (the caller's contract is broken)
    and never binds on top of a held port (FR-37). Returns once the ``/mcp`` edge
    answers — a browser-shaped GET drawing a ``406`` is the healthy ready state
    (FR-9), so any HTTP answer counts.
    """
    if not preflight(inboxes):
        raise RuntimeError("preflight failed: inboxes missing a required queue")
    if port_is_held(host, port):
        raise RuntimeError(f"port {host}:{port} is already held; refusing to bind")

    mcp = build_server(inboxes, name=name)
    url = f"http://{host}:{port}/mcp"

    def _run() -> None:
        mcp.run(transport="http", host=host, port=port, path="/mcp", show_banner=False)

    thread = threading.Thread(target=_run, name=f"{name}-mcp-server", daemon=True)
    thread.start()

    deadline = time.monotonic() + ready_timeout
    while time.monotonic() < deadline:
        if _edge_answers(url, timeout=0.5):
            return ServerHandle(url=url, thread=thread)
        time.sleep(0.05)
    raise TimeoutError(f"server at {url} did not become ready within {ready_timeout}s")


def _edge_answers(url: str, timeout: float = 2.0) -> bool:
    """True once anything HTTP answers at the URL. 406 is the healthy answer."""
    try:
        with urllib.request.urlopen(urllib.request.Request(url, method="GET"), timeout=timeout):
            return True
    except urllib.error.HTTPError:
        return True  # 406 (or any status) proves an edge is up
    except (urllib.error.URLError, OSError):
        return False
