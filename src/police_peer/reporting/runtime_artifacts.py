"""Write the runner's local series summary, including honest token evidence."""

from __future__ import annotations

import json
from pathlib import Path

from common.domain.scoring import Role
from common.transport.series import SeriesResult
from police_peer.evidence.token_ledger import TokenLedger
from police_peer.reporting.replay_bundle import publish_replay_bundle


def write_artifacts(
    artifacts_dir: Path | str,
    result: SeriesResult,
    role: Role = Role.POLICE,
    group_id: str = "police-local",
    mode: str = "warmup",
) -> None:
    """Persist the stable local series summary to the artifacts directory."""
    path = Path(artifacts_dir)
    path.mkdir(parents=True, exist_ok=True)
    summary = {
        "group_id": group_id,
        "mode": mode,
        "natural_role": role.value,
        "game_id": result.game_id,
        "game_uid": result.game_uid,
        "settled": result.settled,
        "settled_outcome": result.settled_outcome.value if result.settled_outcome else None,
        "ledger": [
            {
                "sub_game_number": row.sub_game_number,
                "role": row.role.value,
                "outcome": row.outcome.value,
                "steps": row.steps,
                "score_police": row.score_police,
                "score_thief": row.score_thief,
                "audit_ok": row.audit_ok,
            }
            for row in result.ledger
        ],
    }
    filename = f"result_{result.game_id}.json" if result.game_id else "result.json"
    (path / filename).write_text(json.dumps(summary, indent=2), encoding="utf-8")


def write_series_artifacts(
    artifacts_dir: Path | str,
    result: SeriesResult,
    *,
    role: Role,
    group_id: str,
    mode: str,
    token_ledger: TokenLedger,
) -> None:
    """Write the local summary and, for settled series, its verified replay."""
    write_artifacts(artifacts_dir, result, role=role, group_id=group_id, mode=mode)
    if result.settled:
        publish_replay_bundle(artifacts_dir, result, token_ledger=token_ledger)
