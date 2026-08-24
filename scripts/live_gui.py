"""Launch the Police production runner with its local-truth Live GUI."""

from __future__ import annotations

from functools import partial

from common.domain.scoring import Role
from police_peer.cli import build_parser
from police_peer.live_gui import launch_live_gui
from police_peer.runner import run_one_peer


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    parser.description = __doc__
    parser.add_argument("--auto-start", action="store_true", help="start after Tk opens")
    parser.add_argument("--step-delay", type=float, default=0.15, help="GUI event pacing")
    args = vars(parser.parse_args(argv))
    auto_start = bool(args.pop("auto_start"))
    step_delay = float(args.pop("step_delay"))
    args["role"] = Role.POLICE
    return launch_live_gui(
        partial(run_one_peer, **args), auto_start=auto_start, step_delay=step_delay,
    )


if __name__ == "__main__":
    raise SystemExit(main())
