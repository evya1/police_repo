"""One-peer independent process runner for FastMCP over HTTP."""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from common.config import ConfigError, load_config
from common.domain.scoring import Role
from common.transport.loopback import Inboxes
from common.transport.mcp_client import McpChannel, edge_answers, wait_for_edge
from common.transport.mcp_server import serve_background
from common.transport.negotiate import counter_signed_reply_builder
from common.transport.terms import project_terms
from police_peer.evidence.token_ledger import CountedPlayIneligibleError, assert_counted_eligible
from police_peer.league.readiness import CountedPlayNotReadyError
from police_peer.league.runtime_evidence import prepare_runtime_evidence
from police_peer.reporting.runtime_artifacts import write_series_artifacts
from police_peer.reporting.settlement import publish_kit, settle
from police_peer.sdk import Budgets, __version__, create_peer
from police_peer.strategy import Strategy
from police_peer.wire.config import PrivateConfig, load_private
from police_peer.wire.runtime_services import compose_runtime_services, report_counted_result

logger = logging.getLogger(__name__)


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
    group_code_confirmed: bool = False,
    public_url: str = "",
    email_recipient: str | None = None,
    authorize_email_send: bool = False,
    listener: Callable[[dict], None] | None = None,
) -> int:
    """Run one independent peer process: serve MCP, dial peer, run 6 subgames."""
    try:
        raw_config = load_config(shared_config)
        private = load_private(private_config) if private_config else PrivateConfig()
        services = compose_runtime_services(
            private, raw_config, mode=mode, artifacts_dir=artifacts_dir,
            emit_kit_bundle=emit_kit_bundle, email_recipient=email_recipient,
            authorize_email_send=authorize_email_send,
        )
        runtime = prepare_runtime_evidence(
            private_config=private_config, shared_config=shared_config, group_id=group_id,
            mode=mode, group_code_confirmed=group_code_confirmed, public_url=public_url,
            repo_root=Path(__file__).resolve().parents[2], code_version=__version__,
        )
    except (ConfigError, CountedPlayNotReadyError) as exc:
        logger.error("Startup refused before transport startup: %s", exc)
        return 2
    inboxes = Inboxes()
    reply_terms = project_terms(raw_config, private.__dict__)
    reply_terms["num_games"] = 6
    inboxes.agreement_reply = counter_signed_reply_builder(
        terms=reply_terms, group_id=group_id, natural_role=role,
        identity_block=runtime.greeting_identity,
    )
    serve_background(
        inboxes,
        host=listen_host,
        port=listen_port,
        name=group_id,
        ready_timeout=15.0,
    )
    channel: McpChannel | None = None
    try:
        if not wait_for_edge(peer_url, connect_timeout, probe=edge_answers):
            logger.error("Peer URL %s unreachable within %ss", peer_url, connect_timeout)
            return 7

        budgets = Budgets(turn_timeout, connect_timeout, poll_interval)
        channel = McpChannel(peer_url, inboxes, timeout=turn_timeout)
        configure_endpoints = getattr(channel, "configure_peer_endpoints", None)
        if configure_endpoints is not None:
            configure_endpoints(
                police_url=private.endpoints.opponent_police_url or peer_url,
                thief_url=private.endpoints.opponent_thief_url or peer_url,
                transition_timeout=connect_timeout,
            )

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
            identity_block=runtime.greeting_identity,
            text_provider=services.text_provider,
            token_ledger=runtime.token_ledger,
            listener=listener,
        )

        result = facade.run()
        if mode == "counted":
            try:
                assert_counted_eligible(runtime.token_ledger)
            except CountedPlayIneligibleError as exc:
                logger.error("Counted series refused after token accounting: %s", exc)
                if artifacts_dir:
                    write_series_artifacts(
                        artifacts_dir, result, role=role, group_id=group_id, mode=mode,
                        token_ledger=runtime.token_ledger,
                    )
                return 2
        agreement = settle(
            channel, result, our_group=group_id, budget=turn_timeout,
            token_ledger=runtime.token_ledger, identity=runtime.identity, mode=mode,
        )

        kit_result_path = None
        if artifacts_dir:
            write_series_artifacts(
                artifacts_dir, result, role=role, group_id=group_id, mode=mode,
                token_ledger=runtime.token_ledger,
            )
            if result.settled and emit_kit_bundle:
                kit_result_path = publish_kit(
                    artifacts_dir, result, our_group=group_id, mode=mode,
                    confirmed=agreement.agreed, identity=runtime.identity,
                    opponent_identity=result.opponent_identity,
                    shared_config=raw_config, agreement=agreement,
                )

        if mode == "counted" and not agreement.agreed:
            # The series played and audited cleanly; only the settlement handshake did not
            # complete. The bundle is on disk recording `confirmed: false`, and no report is
            # owed or sent -- reporting alone on an unconfirmed result is what zeroes both.
            logger.error("Counted series is not reportable: %s", agreement.reason)
            return 6
        if not report_counted_result(services, kit_result_path, mode=mode):
            logger.error("Counted series is not reportable: kit projection failed")
            return 6
        return 0 if result.settled else 6
    except Exception as exc:
        logger.exception("Series execution failed: %s", exc)
        return 1
    finally:
        if channel is not None:
            channel.close()
