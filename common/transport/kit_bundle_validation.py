"""Strict validation for one exact Yoram Appendix-F artifact directory."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

from common.transport.atomic_publish import SelfVerifyError
from common.transport.canonical import canonical_bytes, commit
from common.transport.kit_artifact_schemas import CONFIG_SCHEMA, DECLARATION_SCHEMA, LOG_SCHEMA
from common.transport.kit_identity import verify_group_block
from common.transport.kit_names import (
    config_name,
    declaration_name,
    links_block,
    log_name,
    result_name,
)
from common.transport.kit_result_validation import validate_emailed_result

_DECLARATION_KEYS = {
    "_schema", "schema_version", "declaration_type", "game_id", "game_uid", "links",
    "timezone", "game_started_at", "game_ended_at", "num_sub_games", "max_tokens_per_game",
    "groups",
}
_GROUP_KEYS = {
    "group_id", "group_name", "members", "repos", "mcp_servers", "llm_model",
    "hardware_spec", "signature",
}
_HARDWARE_KEYS = {
    "cpu_type", "cpu_freq_mhz", "cpu_cores", "ram_gb", "gpu_model", "vram_gb",
}
_CONFIG_SHARED_KEYS = {
    "schema_version", "_note", "agreed_between", "board_and_agents",
    "movement_and_barriers", "scoring", "pheromones", "network_and_league",
    "rate_limiter_gatekeeper",
}
_CONFIG_KEYS = _CONFIG_SHARED_KEYS | {
    "_schema", "game_id", "game_uid", "sub_game_number", "links", "config_name",
    "config_sha256",
}
_CONFIG_BLOCK_KEYS = {
    "board_and_agents": {"grid_size", "thief_start", "cop_start"},
    "movement_and_barriers": {"move_set", "max_barriers", "max_moves", "survival_threshold"},
    "scoring": {"capture_cop", "capture_thief", "survival_cop", "survival_thief", "tie_score"},
    "pheromones": {"pheromone_center_intensity", "pheromone_decay", "pheromone_grid_size"},
    "network_and_league": {"num_games", "token_budget_per_series"},
    "rate_limiter_gatekeeper": {
        "requests_per_minute", "concurrent_requests", "retry_backoff_sec", "max_retries",
        "queue_depth",
    },
}
_LOG_KEYS = {
    "_schema", "schema_version", "game_id", "game_uid", "links", "summary", "records",
    "mutual_agreement",
}
_SUMMARY_KEYS = {
    "sub_game_number", "group_id", "role", "opponent_group_id", "result", "winner_role",
    "steps", "timezone", "started_at", "ended_at", "duration_seconds", "tokens_total", "audit",
}


def _load(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SelfVerifyError(f"{path.name} is not valid JSON") from exc
    if not isinstance(value, dict):
        raise SelfVerifyError(f"{path.name} is not a JSON object")
    return value


def _exact(label: str, value: dict, keys: set[str]) -> None:
    if set(value) != keys:
        raise SelfVerifyError(f"{label} keys do not match Yoram's reference template")


def _aware(value: object) -> bool:
    try:
        parsed = datetime.fromisoformat(value) if isinstance(value, str) else None
    except ValueError:
        return False
    return bool(parsed and parsed.utcoffset() is not None)


def _validate_common(document: dict, *, game_id: str, game_uid: str) -> None:
    if (document.get("game_id"), document.get("game_uid")) != (game_id, game_uid):
        raise SelfVerifyError("official artifact identifiers mismatch")
    if document.get("schema_version") != "1.1" or document.get("links") != links_block(game_id):
        raise SelfVerifyError("official artifact schema or links mismatch")


def validate_official_bundle(root: Path | str) -> dict:
    """Reload all 14 files and validate exact templates, hashes, commits, and links."""
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
        raise SelfVerifyError(
            f"official file set mismatch: missing={sorted(expected-actual)} "
            f"extra={sorted(actual-expected)}"
        )

    declaration = _load(directory / declaration_name(game_id))
    _exact("declaration", declaration, _DECLARATION_KEYS)
    _validate_common(declaration, game_id=game_id, game_uid=game_uid)
    groups = list(declaration["groups"].values())
    if declaration["_schema"] != DECLARATION_SCHEMA or declaration["timezone"] != "Asia/Jerusalem":
        raise SelfVerifyError("declaration schema or timezone mismatch")
    if declaration["num_sub_games"] != 6 or not isinstance(declaration["max_tokens_per_game"], int):
        raise SelfVerifyError("declaration series limits are incomplete")
    if len(groups) != 2 or not all(_aware(declaration[key]) for key in ("game_started_at", "game_ended_at")):
        raise SelfVerifyError("declaration groups or timestamps are incomplete")
    for group in groups:
        _exact("declaration group", group, _GROUP_KEYS)
        _exact("hardware_spec", group["hardware_spec"], _HARDWARE_KEYS)
        if not verify_group_block(group):
            raise SelfVerifyError("declaration group signature failed")

    for number in range(1, 7):
        config = _load(directory / config_name(game_id, number))
        _exact(f"config g{number:02d}", config, _CONFIG_KEYS)
        _validate_common(config, game_id=game_id, game_uid=game_uid)
        if config["_schema"] != CONFIG_SCHEMA or config["config_name"] != config_name(game_id, number):
            raise SelfVerifyError(f"config g{number:02d} schema or filename mismatch")
        for block, keys in _CONFIG_BLOCK_KEYS.items():
            _exact(f"config g{number:02d} {block}", config[block], keys)
        shared = {key: config[key] for key in _CONFIG_SHARED_KEYS}
        if config["config_sha256"] != hashlib.sha256(canonical_bytes(shared)).hexdigest():
            raise SelfVerifyError(f"config g{number:02d} hash failed")

        log = _load(directory / log_name(game_id, number))
        _exact(f"log g{number:02d}", log, _LOG_KEYS)
        _validate_common(log, game_id=game_id, game_uid=game_uid)
        _exact(f"log g{number:02d} summary", log["summary"], _SUMMARY_KEYS)
        _exact(f"log g{number:02d} audit", log["summary"]["audit"], {"passed", "verified_steps", "failed_steps"})
        _exact(f"log g{number:02d} agreement", log["mutual_agreement"], {"opponent_group_id", "sha256", "confirmed"})
        if log["_schema"] != LOG_SCHEMA or log["summary"]["timezone"] != "Asia/Jerusalem":
            raise SelfVerifyError(f"log g{number:02d} schema or timezone mismatch")
        if not all(_aware(log["summary"][key]) for key in ("started_at", "ended_at")):
            raise SelfVerifyError(f"log g{number:02d} timestamps are incomplete")
        agreement = log["mutual_agreement"]
        records_sha = hashlib.sha256(
            json.dumps(log["records"], ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()
        if agreement["sha256"] != records_sha or agreement["confirmed"] != bool(log["summary"]["audit"]["passed"]):
            raise SelfVerifyError(f"log g{number:02d} mutual agreement mismatch")
        for record in log["records"]:
            _exact(f"log g{number:02d} record", record, {"payload", "nonce", "commit"})
            if commit(record["payload"], record["nonce"]) != record["commit"]:
                raise SelfVerifyError(f"log g{number:02d} commit failed")

    if {group["group_id"] for group in groups} != set(result.get("groups", [])):
        raise SelfVerifyError("declaration and result groups mismatch")
    validate_emailed_result(result, filename=result_paths[0].name)
    return result
