"""One-peer independent process runner for FastMCP over HTTP."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

from common.config import PrivateConfig as DeclaredPrivateConfig
from common.domain.scoring import Role
from common.transport.loopback import Inboxes
from common.transport.mcp_client import McpChannel, edge_answers
from common.transport.mcp_server import serve_background
from common.transport.series import SeriesResult
from police_peer.evidence.identity_source import CountedPlayRefusedError
from police_peer.league.preflight import FilePairingHistoryStore, LeaguePairingGuard
from police_peer.reporting.declaration import (
    agree_on_result,
    declared_private,
    our_identity_block,
)
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


def _publish_kit(
    artifacts_dir, result: SeriesResult, *, group_id: str, mode: str,
    declared_private: DeclaredPrivateConfig | None = None,
    confirmed: bool = False,
) -> None:
    """Publish the kit projection beside the internal bundle.

    Deliberately non-fatal: the internal bundle is the evidence of record and is already on
    disk by the time we get here. A projection that cannot be written is a reporting problem
    to be seen and fixed, not a reason to lose a settled series.
    """
    kwargs: dict = {"confirmed": confirmed}
    declared_private = declared_private or DeclaredPrivateConfig()
    guard = LeaguePairingGuard(history_store=FilePairingHistoryStore())
    ours = our_identity_block(
        declared_private, group_id=group_id,
        counted_games_played=len(guard.get_counted_matches()),
    )
    if ours is not None:
        theirs = {"group_id": result.opponent_group_id}
        pair_sorted = sorted([ours, theirs], key=lambda b: b["group_id"])
        kwargs["groups"] = pair_sorted
    try:
        publish_kit_bundle(
            artifacts_dir, result, our_group=group_id, counted=(mode == "counted"), **kwargs
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
    declared_private_overrides: dict | None = None,
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

        our_private = declared_private(private_config, declared_private_overrides)

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
            declared_private=our_private,
        )

        result = facade.run()

        agreed = True
        if result.settled and emit_kit_bundle:
            # The mutual audit the series engine already performed is a precondition of
            # agreeing (App. E rule 36); agreement is exchanged AFTER settlement, never before.
            outcome = agree_on_result(
                channel, result, our_group=group_id, budget=turn_timeout
            )
            agreed = outcome.agreed
            if not agreed:
                logger.warning("No mutual result agreement: %s", outcome.reason)

        if artifacts_dir:
            write_artifacts(artifacts_dir, result, role=role, group_id=group_id, mode=mode)
            if result.settled:
                publish_replay_bundle(artifacts_dir, result)
                if emit_kit_bundle:
                    _publish_kit(
                        artifacts_dir, result, group_id=group_id, mode=mode,
                        declared_private=our_private, confirmed=agreed,
                    )

        if mode == "counted" and not agreed:
            # Never claim an agreement that did not happen (DEC-10): the bundle above was
            # already published with confirmed=False before this refusal.
            return 6

        return 0 if result.settled else 6
    except CountedPlayRefusedError as exc:
        logger.error("Counted play refused before any game started: %s", exc)
        return 6
    except Exception as exc:
        logger.exception("Series execution failed: %s", exc)
        return 1
    finally:
        if channel is not None:
            channel.close()
