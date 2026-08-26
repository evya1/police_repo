#!/usr/bin/env python3
"""Validate one published official Appendix-F artifact directory."""

from __future__ import annotations

import argparse

from common.transport.kit_bundle_validation import validate_official_bundle


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", help="Directory containing exactly 14 official JSON files")
    args = parser.parse_args()
    result = validate_official_bundle(args.directory)
    print(f"VALID game_id={result['game_id']} game_uid={result['game_uid']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
