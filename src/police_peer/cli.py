"""CLI entry point for police_peer."""

from __future__ import annotations

import argparse
from pathlib import Path

from common.domain.scoring import Role
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
    )


if __name__ == "__main__":
    raise SystemExit(main())
