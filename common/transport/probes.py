"""Probe classification and diagnosis for peer URL health checks.

STUB — to be replaced by the real implementation in ST-13 (T009).
"""

from __future__ import annotations

TOOLS = ("negotiate", "receive_turn", "submit_audit", "receive_control")


def classify_probe(get_status: int | None, post_status: int | None,
                   post_text: str) -> tuple[int, str]:
    """(exit code, message) from the two probes' raw results. Pure, so it is testable.

    406 = ready, 502 = edge up / nothing behind, 421 = Host header not rewritten.
    """
    # STUB: placeholder
    if get_status == 406:
        return 0, "PEER LISTENING — 406 to a browser-shaped GET"
    if post_status is not None and "protocolVersion" in (post_text or ""):
        return 0, f"answered an MCP initialize (GET gave {get_status})"
    return 7, f"neither probe got a peer-shaped answer (GET {get_status}, POST {post_status})"


def diagnose(url: str, timeout: float = 10.0) -> int:
    """Classify a peer URL and say what to do about it. Returns a CLI exit code."""
    # STUB: placeholder
    print(f"probing {url}")
    return 0
