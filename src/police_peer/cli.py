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
        "--group-code", default=None, help="Our declared group id, overriding [game].group_id"
    )
    parser.add_argument(
        "--members", default=None,
        help="Comma-separated member names, overriding [game].members",
    )
    parser.add_argument(
        "--repo-cop-url", default=None, help="Our cop repo URL, overriding [game.repos].cop"
    )
    parser.add_argument(
        "--repo-thief-url", default=None,
        help="Our thief repo URL, overriding [game.repos].thief",
    )
    parser.add_argument(
        "--public-url", default=None,
        help="Our own tunnel URL, overriding [network.mcp_servers] for OUR role",
    )
    return parser


def _declared_private_overrides(args: argparse.Namespace) -> dict:
    """CLI flags that override the declared identity's private-config fields (T057)."""
    overrides: dict = {}
    if args.group_code is not None:
        overrides["group_id"] = args.group_code
    if args.members is not None:
        overrides["members"] = tuple(
            m.strip() for m in args.members.split(",") if m.strip()
        )
    if args.repo_cop_url is not None or args.repo_thief_url is not None:
        overrides["repos_cop"] = args.repo_cop_url
        overrides["repos_thief"] = args.repo_thief_url
    if args.public_url is not None:
        overrides["public_url"] = args.public_url
    return overrides


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
        declared_private_overrides=_declared_private_overrides(args),
    )


if __name__ == "__main__":
    raise SystemExit(main())
