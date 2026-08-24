"""CLI entry point for police_peer."""

from __future__ import annotations

import argparse
from pathlib import Path

from common.domain.scoring import Role
from common.transport.audit_wire import AUDIT_WIRE_PROFILES, DEFAULT_WIRE_PROFILE
from police_peer.runner import run_one_peer


def build_parser() -> argparse.ArgumentParser:
    """Build command line argument parser for police_peer."""
    parser = argparse.ArgumentParser(description="P2P Police Peer Process Runner")
    parser.add_argument("--listen-host", default="127.0.0.1", help="Host to bind FastMCP server")
    parser.add_argument("--listen-port", type=int, default=8101, help="Port to bind FastMCP server")
    parser.add_argument("--peer-url", default="http://127.0.0.1:8102/mcp", help="Peer MCP URL")
    parser.add_argument("--shared-config", default="config/game.json", help="Path to shared game.json")
    parser.add_argument("--private-config", default=None, help="Path to private game.toml")
    parser.add_argument("--group-id", default="police-local", help="Group/peer ID")
    parser.add_argument(
        "--mode",
        default="warmup",
        choices=["warmup", "counted", "competition", "live"],
        help="Execution mode",
    )
    parser.add_argument("--artifacts-dir", default=None, help="Directory to save reporting artifacts")
    parser.add_argument("--seed", type=int, default=0, help="Random seed")
    parser.add_argument("--connect-timeout", type=float, default=30.0, help="Peer connect timeout")
    parser.add_argument("--turn-timeout", type=float, default=30.0, help="Turn response timeout")
    parser.add_argument(
        "--wire-profile",
        default=DEFAULT_WIRE_PROFILE,
        choices=sorted(AUDIT_WIRE_PROFILES),
        help=f"Audit wire profile for the opponent (default: {DEFAULT_WIRE_PROFILE}, the "
             "pinned copthief-league-protocol lane). Pass 'internal' only for a peer that "
             "speaks this project's own flat audit shape.",
    )
    parser.add_argument(
        "--emit-kit-bundle",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Also project the settled series into the league-kit 14-artifact bundle at "
             "<artifacts>/kit/<game_uid>/ (ADR-012). The internal replay bundle is written "
             "either way.",
    )
    parser.add_argument(
        "--group-code-confirmed", action="store_true",
        help="Confirm the configured group code against the human-approved team record; "
             "required for counted play.",
    )
    parser.add_argument(
        "--public-url", default="",
        help="Actual public MCP URL for the counted declaration (overrides [network].public_url).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for running a police peer."""
    parser = build_parser()
    args = parser.parse_args(argv)
    return run_one_peer(
        listen_host=args.listen_host,
        listen_port=args.listen_port,
        peer_url=args.peer_url,
        shared_config=Path(args.shared_config),
        private_config=Path(args.private_config) if args.private_config else None,
        group_id=args.group_id,
        mode=args.mode,
        artifacts_dir=Path(args.artifacts_dir) if args.artifacts_dir else None,
        seed=args.seed,
        role=Role.POLICE,
        connect_timeout=args.connect_timeout,
        turn_timeout=args.turn_timeout,
        wire_profile=args.wire_profile,
        emit_kit_bundle=args.emit_kit_bundle,
        group_code_confirmed=args.group_code_confirmed,
        public_url=args.public_url,
    )


if __name__ == "__main__":
    raise SystemExit(main())
