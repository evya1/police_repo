"""Validate the binding kit result before it reaches an email boundary."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from common.domain.scoring import Outcome
from common.transport.kit_consensus import (
    CONSENSUS_AGGREGATE_KEYS,
    consensus_scope,
    consensus_sha256,
)
from common.transport.kit_names import SCHEMA_VERSION, result_name
from common.transport.kit_settlement import KitSettlementError, series_final


class KitResultValidationError(ValueError):
    """The published final result is not a coherent, agreed six-game result."""


_SHA40 = re.compile(r"^[0-9a-f]{40}$")


def _is_israel_time(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return False
    return parsed.utcoffset() is not None and parsed.utcoffset() == parsed.astimezone(
        ZoneInfo("Asia/Jerusalem")
    ).utcoffset()


def validate_emailed_result(document: object, *, filename: str) -> dict[str, Any]:
    """Return a valid result document or fail before any external-service call."""
    if not isinstance(document, dict):
        raise KitResultValidationError("published Gmail result must be a JSON object")
    try:
        game_id, game_uid = document["game_id"], document["game_uid"]
        groups, rows, final = document["groups"], document["sub_games"], document["final_result"]
        agreement = document["mutual_agreement"]
        _validate_envelope(document, filename, game_id, game_uid, groups, rows)
        _validate_rows(game_id, groups, rows)
        expected_final = series_final(
            rows, tuple(groups), counted=any(final.get("diversity_reward_applied", {}).values()),
            games_played=final.get("games_played_including_this"),
            first_meeting=bool(final.get("first_meeting_between_groups", True)),
        )
        for key in (*CONSENSUS_AGGREGATE_KEYS, "tokens_total_series"):
            if final.get(key) != expected_final[key]:
                raise KitResultValidationError(f"published Gmail result has inconsistent {key}")
        expected_sha = consensus_sha256(consensus_scope(game_id, final, rows))
        if agreement.get("confirmed") is not True or agreement.get("sha256") != expected_sha:
            raise KitResultValidationError("published Gmail result has no verified agreement")
    except KitResultValidationError:
        raise
    except (KeyError, TypeError, KitSettlementError) as exc:
        raise KitResultValidationError("published Gmail result is malformed") from exc
    return document


def _validate_envelope(document, filename, game_id, game_uid, groups, rows) -> None:
    if document.get("schema_version") != SCHEMA_VERSION or not document.get("_schema"):
        raise KitResultValidationError("published Gmail result uses the wrong official schema")
    if document.get("timezone") != "Asia/Jerusalem":
        raise KitResultValidationError("published Gmail result must declare Israel time")
    if document.get("report_type") != "final_game_result":
        raise KitResultValidationError("published Gmail result uses the wrong report type")
    if not isinstance(game_id, str) or not isinstance(game_uid, str) or not game_uid:
        raise KitResultValidationError("published Gmail result identifiers are malformed")
    if filename != result_name(game_id):
        raise KitResultValidationError("published Gmail result filename is inconsistent")
    if not isinstance(groups, list) or len(groups) != 2 or groups != sorted(set(groups)):
        raise KitResultValidationError("published Gmail result groups are malformed")
    if not isinstance(rows, list) or len(rows) != 6:
        raise KitResultValidationError("published Gmail result must contain six sub-games")


def _validate_rows(game_id: str, groups: list[str], rows: list[dict]) -> None:
    if {row.get("sub_game_number") for row in rows} != set(range(1, 7)):
        raise KitResultValidationError("published Gmail result sub-game numbers are incomplete")
    outcomes = {outcome.value for outcome in Outcome}
    for row in rows:
        audit = row.get("audit")
        if not isinstance(audit, dict):
            raise KitResultValidationError("published Gmail result audit is malformed")
        if audit.get("log_verified") is not True or audit.get("tampered") is not False:
            raise KitResultValidationError("published Gmail result contains unverified evidence")
        if row.get("result") not in outcomes or set(row.get("roles", {})) != set(groups):
            raise KitResultValidationError("published Gmail result row is malformed")
        if set(row.get("github_commit", {})) != set(groups) or any(
            not isinstance(value, str) or _SHA40.fullmatch(value) is None
            for value in row["github_commit"].values()
        ):
            raise KitResultValidationError("published Gmail result Git evidence is malformed")
        if set(row.get("tokens", {})) != set(groups) or any(
            isinstance(value, bool) or not isinstance(value, int) or value < 0
            for value in row["tokens"].values()
        ):
            raise KitResultValidationError("published Gmail result token evidence is malformed")
        expected_log = f"log_{game_id}_g{row['sub_game_number']:02d}.json"
        logs = row.get("log_files", {})
        if set(logs) != set(groups) or len(set(logs.values())) != 1:
            raise KitResultValidationError("published Gmail result log references are incomplete")
        if next(iter(logs.values())) != expected_log:
            raise KitResultValidationError("published Gmail result log reference is malformed")
        if not all(_is_israel_time(row.get(key)) for key in ("started_at", "ended_at")):
            raise KitResultValidationError("published Gmail result timestamps are not Israel time")
