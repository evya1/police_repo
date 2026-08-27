"""Validate the exact official result before it reaches the Gmail boundary."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from common.domain.scoring import Outcome
from common.transport.kit_artifact_schemas import RESULT_SCHEMA
from common.transport.kit_consensus import consensus_scope, consensus_sha256
from common.transport.kit_names import SCHEMA_VERSION, links_block, result_name
from common.transport.kit_settlement import KitSettlementError, series_final


class KitResultValidationError(ValueError):
    """The published final result is not a coherent, agreed six-game result."""


_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_RESULT_KEYS = {
    "_schema", "schema_version", "report_type", "game_id", "game_uid", "links", "timezone",
    "groups", "num_sub_games", "sub_games", "final_result", "mutual_agreement",
}
_ROW_KEYS = {
    "sub_game_number", "roles", "started_at", "ended_at", "result", "winner_group", "tie",
    "github_commit", "tokens", "score", "log_files", "audit",
}
_FINAL_KEYS = {
    "total_score", "sub_games_won", "ties", "winner_group", "series_tie",
    "tokens_total_series",
}


def _aware(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        return datetime.fromisoformat(value).utcoffset() is not None
    except ValueError:
        return False


def _exact(value: dict, keys: set[str], label: str) -> None:
    if set(value) != keys:
        raise KitResultValidationError(f"published Gmail result {label} keys are not official")


def validate_emailed_result(document: object, *, filename: str) -> dict[str, Any]:
    """Return an exact, internally coherent result or fail before any external call."""
    if not isinstance(document, dict):
        raise KitResultValidationError("published Gmail result must be a JSON object")
    try:
        _exact(document, _RESULT_KEYS, "root")
        game_id, game_uid = document["game_id"], document["game_uid"]
        groups, rows, final = document["groups"], document["sub_games"], document["final_result"]
        agreement = document["mutual_agreement"]
        _validate_envelope(document, filename, game_id, game_uid, groups, rows)
        _validate_rows(game_id, groups, rows)
        _exact(final, _FINAL_KEYS, "final_result")
        expected = series_final(rows, tuple(groups), counted=False)
        if final != {key: expected[key] for key in _FINAL_KEYS}:
            raise KitResultValidationError("published Gmail result has inconsistent final_result")
        _exact(agreement, {"sha256", "confirmed"}, "mutual_agreement")
        expected_sha = consensus_sha256(consensus_scope(game_id, final, rows))
        if agreement["confirmed"] is not True or agreement["sha256"] != expected_sha:
            raise KitResultValidationError("published Gmail result has no verified agreement")
    except KitResultValidationError:
        raise
    except (KeyError, TypeError, KitSettlementError) as exc:
        raise KitResultValidationError("published Gmail result is malformed") from exc
    return document


def _validate_envelope(document, filename, game_id, game_uid, groups, rows) -> None:
    if document["_schema"] != RESULT_SCHEMA or document["schema_version"] != SCHEMA_VERSION:
        raise KitResultValidationError("published Gmail result uses the wrong official schema")
    if document["links"] != links_block(game_id) or document["timezone"] != "Asia/Jerusalem":
        raise KitResultValidationError("published Gmail result links or timezone are malformed")
    if document["report_type"] != "final_game_result":
        raise KitResultValidationError("published Gmail result uses the wrong report type")
    if not isinstance(game_id, str) or not isinstance(game_uid, str) or not game_uid:
        raise KitResultValidationError("published Gmail result identifiers are malformed")
    if filename != result_name(game_id):
        raise KitResultValidationError("published Gmail result filename is inconsistent")
    if not isinstance(groups, list) or len(groups) != 2 or groups != sorted(set(groups)):
        raise KitResultValidationError("published Gmail result groups are malformed")
    if not isinstance(rows, list) or len(rows) != 6 or document["num_sub_games"] != 6:
        raise KitResultValidationError("published Gmail result must contain six sub-games")


def _validate_rows(game_id: str, groups: list[str], rows: list[dict]) -> None:
    if {row.get("sub_game_number") for row in rows} != set(range(1, 7)):
        raise KitResultValidationError("published Gmail result sub-game numbers are incomplete")
    outcomes = {outcome.value for outcome in Outcome}
    for row in rows:
        _exact(row, _ROW_KEYS, "sub-game")
        audit = row["audit"]
        _exact(audit, {"log_verified", "tampered"}, "audit")
        if audit["log_verified"] is not True or audit["tampered"] is not False:
            raise KitResultValidationError("published Gmail result contains unverified evidence")
        if row["result"] not in outcomes or set(row["roles"]) != set(groups):
            raise KitResultValidationError("published Gmail result row is malformed")
        if set(row["github_commit"]) != set(groups) or any(
            not isinstance(value, str) or _SHA40.fullmatch(value) is None
            for value in row["github_commit"].values()
        ):
            raise KitResultValidationError("published Gmail result Git evidence is malformed")
        if set(row["tokens"]) != set(groups) or any(
            isinstance(value, bool) or not isinstance(value, int) or value < 0
            for value in row["tokens"].values()
        ):
            raise KitResultValidationError("published Gmail result token evidence is malformed")
        expected_log = f"log_{game_id}_g{row['sub_game_number']:02d}.json"
        logs = row["log_files"]
        if set(logs) != set(groups) or set(logs.values()) != {expected_log}:
            raise KitResultValidationError("published Gmail result log references are malformed")
        if not all(_aware(row[key]) for key in ("started_at", "ended_at")):
            raise KitResultValidationError("published Gmail result timestamps are malformed")
