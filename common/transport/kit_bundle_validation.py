"""Strict cross-document validation for one official Appendix-F directory."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from common.transport.atomic_publish import SelfVerifyError
from common.transport.canonical import canonical_bytes, commit
from common.transport.kit_identity import verify_group_block
from common.transport.kit_names import config_name, declaration_name, log_name, result_name
from common.transport.kit_result_validation import validate_emailed_result

_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_CONFIG_OVERLAY = {
    "_schema", "schema_version", "game_id", "game_uid", "sub_game_number", "links",
    "config_name", "config_sha256", "league",
}
_CONFIG_BLOCKS = {
    "agreed_between", "board_and_agents", "movement_and_barriers", "network_and_league",
    "pheromones", "rate_limiter_gatekeeper", "scoring", "world",
}
_GROUP_FIELDS = {
    "group_id", "group_name", "members", "repos", "mcp_servers", "llm_model",
    "hardware_spec", "hardware_spec_sha256", "github_commit", "code_version", "signature",
}


def _is_israel_time(value: object) -> bool:
    try:
        parsed = datetime.fromisoformat(value) if isinstance(value, str) else None
    except ValueError:
        return False
    return bool(parsed and parsed.utcoffset() is not None and parsed.utcoffset() == (
        parsed.astimezone(ZoneInfo("Asia/Jerusalem")).utcoffset()
    ))


def _load(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SelfVerifyError(f"{path.name} is not valid JSON") from exc
    if not isinstance(value, dict):
        raise SelfVerifyError(f"{path.name} is not a JSON object")
    return value


def validate_official_bundle(root: Path | str) -> dict:
    """Validate names, shapes, hashes, evidence and agreement; return the result."""
    directory = Path(root)
    result_paths = list(directory.glob("result_*.json"))
    if len(result_paths) != 1:
        raise SelfVerifyError("official directory must contain exactly one result")
    result = _load(result_paths[0])
    game_id, game_uid = result.get("game_id"), result.get("game_uid")
    expected = {declaration_name(game_id), result_name(game_id)} | {
        name for number in range(1, 7)
        for name in (config_name(game_id, number), log_name(game_id, number))
    }
    actual = {path.name for path in directory.glob("*.json")}
    if actual != expected:
        raise SelfVerifyError(f"official file set mismatch: missing={sorted(expected-actual)} extra={sorted(actual-expected)}")
    declaration = _load(directory / declaration_name(game_id))
    groups = list(declaration.get("groups", {}).values())
    if declaration.get("timezone") != "Asia/Jerusalem" or len(groups) != 2 or not all(
        _is_israel_time(declaration.get(key))
        for key in ("game_started_at", "game_ended_at")
    ):
        raise SelfVerifyError("declaration timezone or groups are incomplete")
    if (declaration.get("game_id"), declaration.get("game_uid")) != (game_id, game_uid):
        raise SelfVerifyError("declaration identifiers mismatch")
    if declaration.get("schema_version") != "1.1" or not declaration.get("_schema"):
        raise SelfVerifyError("declaration official schema mismatch")
    if declaration.get("num_sub_games") != 6 or not isinstance(
        declaration.get("max_tokens_per_game"), int
    ):
        raise SelfVerifyError("declaration series limits are incomplete")
    if not all(set(group) >= _GROUP_FIELDS for group in groups):
        raise SelfVerifyError("declaration identity metadata is incomplete")
    if not all(verify_group_block(group) for group in groups):
        raise SelfVerifyError("declaration group signature failed")
    if not all(_SHA40.fullmatch(group.get("github_commit", "")) for group in groups):
        raise SelfVerifyError("declaration Git evidence is invalid")
    for number in range(1, 7):
        config = _load(directory / config_name(game_id, number))
        if not set(config) >= _CONFIG_BLOCKS:
            raise SelfVerifyError(f"config g{number:02d} agreed structure is incomplete")
        shared = {key: value for key, value in config.items() if key not in _CONFIG_OVERLAY}
        if config.get("config_sha256") != hashlib.sha256(canonical_bytes(shared)).hexdigest():
            raise SelfVerifyError(f"config g{number:02d} hash failed")
        log = _load(directory / log_name(game_id, number))
        summary = log.get("summary", {})
        if summary.get("timezone") != "Asia/Jerusalem" or not all(
            _is_israel_time(summary.get(key)) for key in ("started_at", "ended_at")
        ):
            raise SelfVerifyError(f"log g{number:02d} is not Israel time")
        for half in ("records", "opponent_records"):
            for record in log.get(half) or []:
                if commit(record["payload"], record["nonce"]) != record["commit"]:
                    raise SelfVerifyError(f"log g{number:02d} commit failed")
        for document in (config, log):
            if (document.get("game_id"), document.get("game_uid")) != (game_id, game_uid):
                raise SelfVerifyError(f"g{number:02d} identifiers mismatch")
            if document.get("schema_version") != "1.1" or not document.get("_schema"):
                raise SelfVerifyError(f"g{number:02d} official schema mismatch")
            if document.get("links", {}).get("result") != result_name(game_id):
                raise SelfVerifyError(f"g{number:02d} links mismatch")
    if {group.get("group_id") for group in groups} != set(result.get("groups", [])):
        raise SelfVerifyError("declaration and result groups mismatch")
    validate_emailed_result(result, filename=result_paths[0].name)
    return result
