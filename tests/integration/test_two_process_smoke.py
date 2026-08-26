"""Two-process independent runner smoke test over FastMCP HTTP."""

from __future__ import annotations

import concurrent.futures
import json
import socket
from pathlib import Path

import pytest

pytest.importorskip("fastmcp")

from common.domain.scoring import Role
from common.transport.kit_bundle_validation import validate_official_bundle
from police_peer.runner import run_one_peer


def _free_port() -> int:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def _private(path: Path, group: str, port: int) -> Path:
    path.write_text(
        f'[game]\ngroup_name = "{group}"\ngroup_id = "{group}"\n'
        f'members = ["{group}-member"]\n'
        'repos = { cop = "https://example.invalid/cop", thief = "https://example.invalid/thief" }\n'
        f'[network]\npublic_url = "http://127.0.0.1:{port}/mcp"\n'
        '[llm]\nprovider = "template"\nmodel = "template"\n'
        '[email]\nmode = "off"\nrecipient = "recipient@example.invalid"\n'
    )
    return path


def test_two_process_mcp_runner_e2e(tmp_path: Path) -> None:
    """Run two independent peer facades over localhost HTTP via run_one_peer."""
    port_p = _free_port()
    port_t = _free_port()

    art_p = tmp_path / "police"
    art_t = tmp_path / "thief"
    config = json.loads(Path("config/game.json").read_text())
    config["agreed_between"] = ["police-smoke", "thief-smoke"]
    shared = tmp_path / "game.json"
    shared.write_text(json.dumps(config))
    private_p = _private(tmp_path / "police.toml", "police-smoke", port_p)
    private_t = _private(tmp_path / "thief.toml", "thief-smoke", port_t)

    def _run_police() -> int:
        return run_one_peer(
            listen_host="127.0.0.1",
            listen_port=port_p,
            peer_url=f"http://127.0.0.1:{port_t}/mcp",
            shared_config=shared,
            private_config=private_p,
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
            shared_config=shared,
            private_config=private_t,
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

    police = next((art_p / "official").iterdir())
    thief = next((art_t / "official").iterdir())
    assert validate_official_bundle(police)["mutual_agreement"]["confirmed"] is True
    assert validate_official_bundle(thief)["mutual_agreement"]["confirmed"] is True
