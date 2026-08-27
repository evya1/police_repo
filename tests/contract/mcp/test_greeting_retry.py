"""Real FastMCP reconnect preserves the established SG2 greeting bytes."""

from __future__ import annotations

import concurrent.futures
import json
from copy import deepcopy
from pathlib import Path

import pytest

pytest.importorskip("fastmcp")

from common.domain.scoring import Role  # noqa: E402
from police_peer.sdk import create_peer  # noqa: E402
from tests.contract.mcp.test_local_mcp_smoke import two_peers as two_peers  # noqa: E402, F401


class _RecordingClient:
    def __init__(self, client, attempted: list[dict], *, fail_sg2: bool) -> None:
        self.client = client
        self.attempted = attempted
        self.fail_sg2 = fail_sg2

    async def call_tool(self, tool: str, args: dict):
        message = args.get("message", {})
        if tool == "negotiate" and message.get("sub_game_number") == 2:
            self.attempted.append(deepcopy(message))
            if self.fail_sg2:
                self.fail_sg2 = False
                raise ConnectionError("forced first SG2 client attempt failure")
        return await self.client.call_tool(tool, args)

    async def __aexit__(self, *args):
        return await self.client.__aexit__(*args)


def test_subgame_two_retry_reconnects_and_resends_exact_greeting(two_peers) -> None:
    police_ch, thief_ch, _, _ = two_peers
    attempted: list[dict] = []
    session = police_ch._session
    session.client = _RecordingClient(session.client, attempted, fail_sg2=True)
    connect = session.connect

    def reconnect(*, timeout: float | None = None) -> None:
        connect(timeout=timeout)
        session.client = _RecordingClient(session.client, attempted, fail_sg2=False)

    session.connect = reconnect
    config = json.loads(Path("config/game.json").read_text(encoding="utf-8"))
    police = create_peer(
        config, channel=police_ch, role=Role.POLICE, group_id="retry-police",
        text_provider=None,
    )
    thief = create_peer(
        config, channel=thief_ch, role=Role.THIEF, group_id="retry-thief",
        text_provider=None,
    )

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        police_future = executor.submit(police.run)
        thief_future = executor.submit(thief.run)
        result_p = police_future.result(timeout=60)
        result_t = thief_future.result(timeout=60)

    assert len(attempted) == 2
    assert attempted[0] == attempted[1]
    assert attempted[0]["sub_game_number"] == 2
    assert attempted[0]["nonce"]
    assert len(result_p.ledger) == len(result_t.ledger) == 6
    assert all(row.audit_ok for row in result_p.ledger)
    assert all(row.audit_ok for row in result_t.ledger)
