"""Create an offline preview through the production Gmail reporting boundary.

This helper is intentionally incapable of live delivery. It validates one settled kit result,
uses the central external-service Gatekeeper, and writes a MIME preview plus sanitized receipt
under the chosen artifact root. Production delivery exists only in the counted peer runner and
requires its explicit ``--authorize-email-send`` flag.

The preview recipient is read from ``GMAIL_TEST_RECIPIENT``. Its value is local runtime
configuration and must never be committed, logged, or copied into artifacts other than the
deliberately local MIME preview.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from common.config import ConfigError, load_config
from police_peer.wire.gmail_composition import compose_gmail_reporter
from police_peer.wire.identity_config import EmailSettings
from police_peer.wire.llm_composition import compose_external_gatekeeper


def build_parser() -> argparse.ArgumentParser:
    """Build the dry-run-only command line."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result", type=Path, help="Settled result_<game_id>.json")
    parser.add_argument(
        "--artifact-root", type=Path, required=True,
        help="Private local root where the outbox preview is written",
    )
    parser.add_argument(
        "--shared-config", type=Path, default=Path("config/game.json"),
        help="Shared config used to construct the central Gatekeeper",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Validate and compose locally; this function has no live-send branch."""
    args = build_parser().parse_args(argv)
    if not args.result.is_file():
        print("ERROR: result file not found", file=sys.stderr)
        return 2
    recipient = os.environ.get("GMAIL_TEST_RECIPIENT", "").strip()
    if not recipient:
        print("ERROR: GMAIL_TEST_RECIPIENT is required for local preview", file=sys.stderr)
        return 2
    try:
        config = load_config(args.shared_config)
        gatekeeper = compose_external_gatekeeper(config)
        reporter = compose_gmail_reporter(
            EmailSettings(recipient, "dry-run"),
            args.artifact_root,
            gatekeeper,
            recipient=recipient,
        )
        if reporter is None:  # pragma: no cover - dry-run always enables the reporter
            raise ConfigError("Gmail preview composition is disabled")
        receipt = reporter.report(args.result)
    except Exception as exc:  # noqa: BLE001 - CLI returns a safe generic failure
        print(f"ERROR: preview failed ({type(exc).__name__})", file=sys.stderr)
        return 1
    print(
        "Gmail preview composed locally; API contacted="
        f"{receipt.gmail_api_contacted}; accepted={receipt.gmail_api_accepted}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
