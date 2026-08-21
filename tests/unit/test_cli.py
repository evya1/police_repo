"""Unit tests for the police_peer CLI entry point."""

from __future__ import annotations

from police_peer.cli import build_parser


def test_build_parser_defaults() -> None:
    parser = build_parser()
    args = parser.parse_args([])
    assert args.listen_host == "127.0.0.1"
    assert args.listen_port == 8101
    assert args.peer_url == "http://127.0.0.1:8102/mcp"
    assert args.shared_config == "config/game.json"
    assert args.group_id == "police-local"
    assert args.mode == "warmup"


def test_build_parser_custom_args() -> None:
    parser = build_parser()
    args = parser.parse_args(
        [
            "--listen-host",
            "0.0.0.0",
            "--listen-port",
            "9000",
            "--peer-url",
            "http://example.com/mcp",
            "--shared-config",
            "custom.json",
            "--group-id",
            "custom-police",
            "--mode",
            "competition",
            "--artifacts-dir",
            "/tmp/artifacts",
            "--seed",
            "123",
        ]
    )
    assert args.listen_host == "0.0.0.0"
    assert args.listen_port == 9000
    assert args.peer_url == "http://example.com/mcp"
    assert args.shared_config == "custom.json"
    assert args.group_id == "custom-police"
    assert args.mode == "competition"
    assert args.artifacts_dir == "/tmp/artifacts"
    assert args.seed == 123
