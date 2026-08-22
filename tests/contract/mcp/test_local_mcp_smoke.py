"""Local FastMCP smoke: two peers complete the full surface over real HTTP.

This is the ``local_mcp_smoke`` proof (SC-1) exercised inside one test process
with two real FastMCP servers and two real ``McpChannel`` clients on
``localhost`` — handshake, six sub-games, mutual audits — with no public
endpoint. The sibling two-OS-process run (``police_repo`` vs ``thief_repo``)
uses the same channel and server; this test proves the transport itself.

These tests require ``fastmcp`` installed. They never run in the zero-dependency
spine (which stays on loopback).
"""

from __future__ import annotations

import socket

import pytest

pytest.importorskip("fastmcp")

from common.domain.scoring import Role, role_for  # noqa: E402
from common.transport.loopback import Inboxes  # noqa: E402
from common.transport.mcp_client import McpChannel, edge_answers  # noqa: E402
from common.transport.mcp_server import TOOL_NAMES, serve_background  # noqa: E402
from common.transport.series import PeerConfig, SeriesResult, run_series  # noqa: E402
from police_peer.wire import BrainDrivenEngine  # noqa: E402


class DummyBudgets:
    turn_timeout = 30.0
    connect_timeout = 30.0
    poll_interval = 0.01


_full_terms = {
    "board_size": 7,
    "smell_grid_size": 5,
    "decay_per_step": 0.1,
    "emit_intensity": 0.9,
    "min_center_intensity": 0.5,
    "max_steps": 35,
    "barriers_max": 14,
    "setting": "New York",
    "hint_max_words": 15,
    "axis_origin_corner": "top-left",
    "axis_start_index": 0,
    "thief_start": [3, 3],
    "cop_start": [0, 0],
    "num_games": 6,
}


def _free_port() -> int:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


@pytest.fixture
def two_peers():
    """Stand up two real servers + two channels cross-connected on localhost."""
    police_inbox, thief_inbox = Inboxes(), Inboxes()
    police_port, thief_port = _free_port(), _free_port()
    police_srv = serve_background(police_inbox, port=police_port, name="police")
    thief_srv = serve_background(thief_inbox, port=thief_port, name="thief")
    # Police sends to Thief's server and drains its own inbox; Thief mirrored.
    police_ch = McpChannel(thief_srv.url, police_inbox)
    thief_ch = McpChannel(police_srv.url, thief_inbox)
    yield police_ch, thief_ch, police_srv, thief_srv
    police_ch.close()
    thief_ch.close()


def test_edge_answers_406(two_peers) -> None:
    """FR-9: a browser-shaped GET on the /mcp edge answers (406), proving readiness."""
    _, _, police_srv, thief_srv = two_peers
    assert edge_answers(police_srv.url)
    assert edge_answers(thief_srv.url)


def test_full_series_over_real_http(two_peers) -> None:
    """TC-21 / SC-1: full six-sub-game series settles over real localhost HTTP."""
    police_ch, thief_ch, _, _ = two_peers
    config_p = PeerConfig(natural_role=Role.POLICE, budgets=DummyBudgets(), terms=_full_terms, seed=42)
    config_t = PeerConfig(natural_role=Role.THIEF, budgets=DummyBudgets(), terms=_full_terms, seed=42)
    result_p, result_t = run_series(
        police_ch, thief_ch, config_p, config_t,
        BrainDrivenEngine(Role.POLICE, config={}), BrainDrivenEngine(Role.THIEF, config={}),
    )
    assert isinstance(result_p, SeriesResult) and isinstance(result_t, SeriesResult)
    assert len(result_p.ledger) == 6 and len(result_t.ledger) == 6
    for i, row in enumerate(result_p.ledger, start=1):
        assert row.role is role_for(Role.POLICE, i)
    assert all(row.audit_ok for row in result_p.ledger)
    assert all(row.audit_ok for row in result_t.ledger)
    assert result_p.settled and result_t.settled
    assert result_p.game_id != "" and result_p.game_uid != ""
    # Both sides derived the same game identity over the wire (US-MCP-001).
    assert result_p.game_id == result_t.game_id
    assert result_p.game_uid == result_t.game_uid


def test_tools_listed_over_http(two_peers) -> None:
    """TC-01: all four tools are listed under their exact names on the live server."""
    police_ch, _, _, _ = two_peers

    async def _list():
        return await police_ch._client.list_tools()

    tools = police_ch._submit(_list())
    names = {t.name for t in tools}
    assert names == set(TOOL_NAMES), f"expected {TOOL_NAMES}, got {sorted(names)}"
    assert "receive_control" in names


def test_argument_asymmetry_over_http(two_peers) -> None:
    """TC-02: submit_audit called with `message` (not `payload`) is a schema error over HTTP."""
    police_ch, _, _, _ = two_peers

    async def _bad():
        # submit_audit's parameter is `payload`; sending `message` must be rejected.
        return await police_ch._client.call_tool("submit_audit", {"message": {"x": 1}})

    with pytest.raises(Exception):  # noqa: B017 — any FastMCP validation error is acceptable
        police_ch._submit(_bad())
