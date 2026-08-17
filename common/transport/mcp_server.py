"""FastMCP server: four tools, lazy import, no blocking in handlers.

STUB — to be replaced by the real implementation in ST-10 (T009).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def build_server(inboxes: Any) -> Any:
    """Construct the FastMCP app. Imported lazily so the zero-dependency tier stays honest."""
    # STUB: placeholder — the real implementation will import fastmcp here
    # and register the four tools: negotiate, receive_turn, submit_audit,
    # receive_control.
    return None


def port_is_held(host: str, port: int) -> bool:
    """A connect probe, never a trial bind.

    FR-37: never bind to test — race the real server for the address.
    """
    # STUB: placeholder
    import socket
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


def preflight(cfg: Any) -> bool:
    """Run the shared-layer guard scan. Refuse to start on violation.

    FR-39: no fastmcp import outside this module and mcp_client.
    """
    # STUB: placeholder
    return True


def serve(cfg: Any, *, host: str, port: int, peer_url: str | None,
          artifacts: Path, await_peer: bool = False) -> int:
    """Stand the peer up. Preflight first — the server never binds a port if it refuses."""
    # STUB: placeholder
    return 0
