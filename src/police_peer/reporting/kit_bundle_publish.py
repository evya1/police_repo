"""Atomic publication and post-write verification for league-kit bundles."""

from __future__ import annotations

import json
from pathlib import Path

from common.transport.atomic_publish import Checkpoint, SelfVerifyError, publish_atomic
from common.transport.canonical import commit as recompute_commit
from common.transport.series import SeriesResult


def _self_verify(staging: Path) -> None:
    """Reload every written log and reproduce every commit before publication."""
    problems: list[str] = []
    for path in sorted(staging.glob("log_*.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        for half in ("records", "opponent_records"):
            for index, record in enumerate(document.get(half) or []):
                recomputed = recompute_commit(record["payload"], record["nonce"])
                if recomputed != record["commit"]:
                    problems.append(f"{path.name} {half}[{index}] does not reproduce its commit")
    if problems:
        raise SelfVerifyError("; ".join(problems[:6]))


def publish_kit_bundle(
    artifact_root: Path | str,
    result: SeriesResult,
    *,
    on_checkpoint: Checkpoint | None = None,
    include_tokens: bool = True,
    **kwargs,
) -> Path:
    """Build, verify, and atomically publish one league-kit bundle."""
    from police_peer.reporting.kit_bundle import KIT_SUBDIR, build_kit_bundle

    files = build_kit_bundle(result, include_tokens=include_tokens, **kwargs)
    return publish_atomic(
        Path(artifact_root) / KIT_SUBDIR,
        result.game_uid,
        files,
        _self_verify,
        on_checkpoint=on_checkpoint,
    )
