"""One-peer independent process runner for FastMCP over HTTP."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

from common.domain.scoring import Role
from common.transport.loopback import Inboxes
from common.transport.mcp_client import McpChannel, edge_answers
from common.transport.mcp_server import serve_background
from common.transport.series import SeriesResult
from police_peer.reporting.kit_bundle import publish_kit_bundle
from police_peer.reporting.replay_bundle import publish_replay_bundle
from police_peer.sdk import Budgets, create_peer
from police_peer.strategy import Strategy

logger = logging.getLogger(__name__)


def write_artifacts(
    artifacts_dir: Path | str,
    result: SeriesResult,
    role: Role = Role.POLICE,
    group_id: str = "police-local",
    mode: str = "warmup",
) -> None:
    """Persist series results and ledger to the artifacts directory."""
    path = Path(artifacts_dir)
    path.mkdir(parents=True, exist_ok=True)
    summary = {
        "group_id": group_id,
        "mode": mode,
        "natural_role": role.value,
        "game_id": result.game_id,
        "game_uid": result.game_uid,
        "settled": result.settled,
        "settled_outcome": result.settled_outcome.value if result.settled_outcome else None,
        "ledger": [
            {
                "sub_game_number": row.sub_game_number,
                "role": row.role.value,
                "outcome": row.outcome.value,
                "steps": row.steps,
                "score_police": row.score_police,
                "score_thief": row.score_thief,
                "audit_ok": row.audit_ok,
            }
            for row in result.ledger
        ],
    }
    filename = f"result_{result.game_id}.json" if result.game_id else "result.json"
    (path / filename).write_text(json.dumps(summary, indent=2), encoding="utf-8")


def _publish_kit(artifacts_dir, result: SeriesResult, *, group_id: str, mode: str) -> None:
    """Publish the kit projection beside the internal bundle.

    Deliberately non-fatal: the internal bundle is the evidence of record and is already on
    disk by the time we get here. A projection that cannot be written is a reporting problem
    to be seen and fixed, not a reason to lose a settled series.
    """
    try:
        publish_kit_bundle(
            artifacts_dir, result, our_group=group_id, counted=(mode == "counted")
        )
    except Exception as exc:  # noqa: BLE001 - never let a projection fault destroy evidence
        logger.error("Kit bundle projection failed (internal bundle is intact): %s", exc)


def run_one_peer(
    *,
    listen_host: str = "127.0.0.1",
    listen_port: int = 8101,
    peer_url: str = "http://127.0.0.1:8102/mcp",
    shared_config: Path | str = "config/game.json",
    private_config: Path | str | None = None,
    group_id: str = "police-local",
    mode: str = "warmup",
    artifacts_dir: Path | str | None = None,
    seed: int = 0,
    role: Role = Role.POLICE,
    strategy: Strategy | None = None,
    connect_timeout: float = 30.0,
    turn_timeout: float = 30.0,
    poll_interval: float = 0.01,
    wire_profile: str | None = None,
    emit_kit_bundle: bool = True,
) -> int:
    """Run one independent peer process: serve MCP, dial peer, run 6 subgames."""
    inboxes = Inboxes()
    serve_background(
        inboxes,
        host=listen_host,
        port=listen_port,
        name=group_id,
        ready_timeout=15.0,
    )
    channel: McpChannel | None = None
    try:
        deadline = time.monotonic() + connect_timeout
        connected = False
        while time.monotonic() < deadline:
            if edge_answers(peer_url, timeout=0.5):
                connected = True
                break
            time.sleep(0.05)

        if not connected:
            logger.error("Peer URL %s unreachable within %ss", peer_url, connect_timeout)
            return 7

        budgets = Budgets(
            turn_timeout=turn_timeout,
            connect_timeout=connect_timeout,
            poll_interval=poll_interval,
        )
        channel = McpChannel(peer_url, inboxes, timeout=turn_timeout)

        facade = create_peer(
            config_path=shared_config,
            private_config_path=private_config,
            channel=channel,
            # Pass through, do NOT default to BaselineStrategy() here: an
            # explicit strategy opts into the legacy stand-in path; otherwise
            # create_peer wires the real configured brain (BrainDrivenEngine)
            # for POLICE sub-games.
            strategy=strategy,
            role=role,
            seed=seed,
            group_id=group_id,
            budgets=budgets,
            mode=mode,
            wire_profile=wire_profile,
        )

        result = facade.run()

        if artifacts_dir:
            write_artifacts(artifacts_dir, result, role=role, group_id=group_id, mode=mode)
            if result.settled:
                publish_replay_bundle(artifacts_dir, result)
                if emit_kit_bundle:
                    _publish_kit(artifacts_dir, result, group_id=group_id, mode=mode)

        return 0 if result.settled else 6
    except Exception as exc:
        logger.exception("Series execution failed: %s", exc)
        return 1
    finally:
        if channel is not None:
            channel.close()
