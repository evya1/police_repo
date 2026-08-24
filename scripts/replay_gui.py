"""Launch or headlessly verify the repository-integrated Replay GUI."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from police_peer.replay_gui import ReplayGuiError, launch_replay_gui, verify_replay_log


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="kit log JSON or bundle directory")
    parser.add_argument("--config-dir", type=Path, default=Path("config"))
    parser.add_argument("--verify-only", action="store_true", help="verify without opening Tk")
    args = parser.parse_args(argv)
    try:
        if args.verify_only:
            ok, report = verify_replay_log(args.source)
            print(report)
            return 0 if ok else 6
        return launch_replay_gui(args.source, config_dir=args.config_dir)
    except ReplayGuiError as exc:
        print(f"replay GUI error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
