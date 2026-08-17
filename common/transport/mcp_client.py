"""FastMCP client: one session, re-establish once, async-free facade.

STUB — to be replaced by the real implementation in ST-11 (T009).
"""

from __future__ import annotations


class PeerUnreachableError(Exception):
    """Raised when the opponent cannot be reached."""


class McpClient:
    """The four calls, with the argument-name asymmetry the reference defines.

    submit_audit takes payload; the other three take message.
    """

    def __init__(self, url: str, timeout: float = 30.0) -> None:
        self.url = url
        self.timeout = timeout
        self._session = None

    def negotiate(self, message: dict) -> dict:
        # STUB: placeholder
        return {"ok": True}

    def receive_turn(self, message: dict) -> dict:
        # STUB: placeholder
        return {"ok": True}

    def submit_audit(self, payload: dict) -> dict:
        # STUB: placeholder — note the `payload` argument name
        return {"ok": True}

    def receive_control(self, message: dict) -> dict:
        # STUB: placeholder
        return {"ok": True}

    def close(self) -> None:
        # STUB: placeholder
        pass


def edge_answers(url: str, timeout: float = 2.0) -> bool:
    """True once ANYTHING HTTP answers at the URL.

    406 is the healthy answer, but any status proves an edge is up.
    """
    # STUB: placeholder
    import urllib.request
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:  # noqa: BLE001
        return False
