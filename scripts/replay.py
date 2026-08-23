"""Headless replay CLI (T047).

Argument parsing, printing, and exit-code mapping only. All loading, membership/digest
validation, config-log pairing, and verification math live behind
``police_peer.sdk.verify_replay_bundle`` — this file imports nothing else.

Exit codes: 0 verified, 4 illegal, 5 invalid/incomplete, 6 tampered, 2 path/usage error.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from police_peer.sdk import verify_replay_bundle

_EXIT_BY_VERDICT = {
    "verified_ok": 0,
    "illegal": 4,
    "invalid": 5,
    "incomplete": 5,
    "tampered": 6,
}


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="replay", description="Verify one published internal-interop replay bundle."
    )
    parser.add_argument("bundle_dir", type=Path, help="path to the UID bundle directory")
    parser.add_argument("--json", action="store_true", help="emit a machine-readable JSON report")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        report = verify_replay_bundle(args.bundle_dir)
    except Exception as exc:  # noqa: BLE001 - any load/path failure is a usage error here
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(report.to_json(), indent=2, sort_keys=True))
    else:
        print(report.to_human())
    return _EXIT_BY_VERDICT.get(report.verdict.value, 5)


if __name__ == "__main__":
    sys.exit(main())
