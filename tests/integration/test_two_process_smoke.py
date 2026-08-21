"""Two-process independent runner smoke test over FastMCP HTTP."""

from __future__ import annotations

import concurrent.futures
import socket
from pathlib import Path

import pytest

pytest.importorskip("fastmcp")

from common.domain.scoring import Role
from police_peer.runner import run_one_peer


def _free_port() -> int:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def test_two_process_mcp_runner_e2e(tmp_path: Path) -> None:
    """Run two independent peer facades over localhost HTTP via run_one_peer."""
    port_p = _free_port()
    port_t = _free_port()

    art_p = tmp_path / "police"
    art_t = tmp_path / "thief"

    def _run_police() -> int:
        return run_one_peer(
            listen_host="127.0.0.1",
            listen_port=port_p,
            peer_url=f"http://127.0.0.1:{port_t}/mcp",
            shared_config=Path("config/game.json"),
            group_id="police-smoke",
            artifacts_dir=art_p,
            role=Role.POLICE,
            connect_timeout=15.0,
            turn_timeout=15.0,
        )

    def _run_thief() -> int:
        return run_one_peer(
            listen_host="127.0.0.1",
            listen_port=port_t,
            peer_url=f"http://127.0.0.1:{port_p}/mcp",
            shared_config=Path("config/game.json"),
            group_id="thief-smoke",
            artifacts_dir=art_t,
            role=Role.THIEF,
            connect_timeout=15.0,
            turn_timeout=15.0,
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        fut_p = executor.submit(_run_police)
        fut_t = executor.submit(_run_thief)
        exit_p = fut_p.result(timeout=30.0)
        exit_t = fut_t.result(timeout=30.0)

    assert exit_p == 0
    assert exit_t == 0

    assert (art_p / "result_police-smoke-vs-thief-smoke.json").exists()
    assert (art_t / "result_police-smoke-vs-thief-smoke.json").exists()
