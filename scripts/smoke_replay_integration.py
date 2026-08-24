"""Public-SDK smoke test for the replay pipeline (T047, shared TEST_AND_INTEGRATION_STRATEGY).

Drives an existing loopback six-sub-game series through the public SDK/composition path
(``create_peer``), publishes the bundle, reloads it through ``verify_replay_bundle``, and
prints one machine-readable summary. Never constructs records or computes hashes itself —
that is entirely ``replay_bundle.py`` / ``replay_service.py``'s job.
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
from pathlib import Path

from common.domain.scoring import Role
from common.transport.loopback import pair
from common.transport.series import PeerFacade, SeriesResult
from police_peer.reporting.kit_bundle import publish_kit_bundle
from police_peer.reporting.replay_bundle import publish_replay_bundle
from police_peer.sdk import Budgets, create_peer, verify_replay_bundle


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Loopback replay smoke test (T047).")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--private-config", type=Path, default=None)
    parser.add_argument("--artifact-root", required=True, type=Path)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def _run_pair(config: Path, private_config: Path | None, seed: int) -> SeriesResult:
    """Two real SDK-composed peers over one loopback pair; return the police-side result."""
    channel_a, channel_b = pair("smoke-police", "smoke-thief")
    budgets = Budgets(turn_timeout=10.0, connect_timeout=10.0, poll_interval=0.005)
    police = create_peer(
        config, private_config_path=private_config, channel=channel_a,
        role=Role.POLICE, seed=seed, group_id="smoke-police", budgets=budgets,
    )
    thief = create_peer(
        config, private_config_path=private_config, channel=channel_b,
        role=Role.THIEF, seed=seed, group_id="smoke-thief", budgets=budgets,
    )

    results: dict[str, SeriesResult] = {}
    errors: list[Exception] = []

    def _go(name: str, facade: PeerFacade) -> None:
        try:
            results[name] = facade.run()
        except Exception as exc:  # noqa: BLE001 - surfaced to the caller below
            errors.append(exc)

    threads = [
        threading.Thread(target=_go, args=("police", police)),
        threading.Thread(target=_go, args=("thief", thief)),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    if errors:
        raise errors[0]
    return results["police"]


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    result = _run_pair(args.config, args.private_config, args.seed)
    if not result.settled:
        print(json.dumps({"error": "series did not settle"}), file=sys.stderr)
        return 1

    bundle_dir = publish_replay_bundle(args.artifact_root, result)
    kit_dir = publish_kit_bundle(
        args.artifact_root, result, our_group="smoke-police", counted=False
    )
    report = verify_replay_bundle(bundle_dir)
    c = report.coverage
    summary = {
        "bundle_dir": str(bundle_dir),
        "kit_bundle_dir": str(kit_dir),
        "game_id": result.game_id,
        "game_uid": result.game_uid,
        "settled_outcome": result.settled_outcome.value,
        "replay_verdict": report.verdict.value,
        "coverage": {
            "integrity": c.integrity, "live_binding": c.live_binding, "physics": c.physics,
            "outcome": c.outcome, "bundle_digests": c.bundle_digests,
            "external_authenticity": c.external_authenticity,
        },
    }
    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print(f"bundle: {bundle_dir}")
        print(f"kit bundle: {kit_dir}")
        print(report.to_human())
    return 0 if report.verdict.value == "verified_ok" else 1


if __name__ == "__main__":
    sys.exit(main())
