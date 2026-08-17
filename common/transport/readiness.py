"""Readiness discipline: probe classification, loopback nonce proof, await-peer.

STUB — to be replaced by the real implementation in ST-13 (T009).
"""

from __future__ import annotations


def probe_classification(url: str, timeout: float = 2.0) -> tuple[int, str]:
    """Classify what a URL is answering. Returns (exit_code, message).

    STUB: placeholder — delegates to probes.classify_probe.
    """
    # STUB: placeholder
    return 7, "not yet implemented"


def loopback_nonce_proof(port: int, hostname: str) -> bool:
    """Bind a throwaway listener, fetch own public hostname, demand back a nonce.

    Refuses to run if the port is already held.
    """
    # STUB: placeholder
    return True


def await_peer(peer_url: str, budget: float, poll_interval: float) -> bool:
    """Poll the opponent's edge for one handshake budget.

    FR-36: same budget the arrived peer gets.
    """
    # STUB: placeholder
    from common.transport.probes import edge_answers
    return edge_answers(peer_url, budget)
