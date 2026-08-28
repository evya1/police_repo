"""Pure builders for Yoram Segal's four official Appendix-F JSON templates."""

from __future__ import annotations

import hashlib
import json

from common.transport.canonical import canonical_bytes
from common.transport.kit_artifact_schemas import (
    CONFIG_SCHEMA,
    DECLARATION_SCHEMA,
    LOG_SCHEMA,
    RESULT_SCHEMA,
)
from common.transport.kit_names import SCHEMA_VERSION, config_name, links_block
from common.transport.kit_records import KitDocumentError, build_summary, check_records

__all__ = [
    "KitDocumentError", "build_config", "build_declaration", "build_log", "build_result",
    "build_summary", "official_config_terms", "official_final_result",
]

CONFIG_NOTE = (
    "Shared, agreed game terms. BOTH peers must hold a byte-identical copy; the pre-game "
    "signature exchange refuses to play on any mismatch. This overlays the private per-peer "
    "game.toml. Book: Appendix F."
)
CONFIG_BLOCK_FIELDS = {
    "board_and_agents": ("grid_size", "thief_start", "cop_start"),
    "movement_and_barriers": ("move_set", "max_barriers", "max_moves", "survival_threshold"),
    "scoring": ("capture_cop", "capture_thief", "survival_cop", "survival_thief", "tie_score"),
    "pheromones": (
        "pheromone_center_intensity", "pheromone_decay", "pheromone_grid_size",
    ),
    "network_and_league": ("num_games", "token_budget_per_series"),
    "rate_limiter_gatekeeper": (
        "requests_per_minute", "concurrent_requests", "retry_backoff_sec", "max_retries",
        "queue_depth",
    ),
}
GROUP_FIELDS = (
    "group_id", "group_name", "members", "repos", "mcp_servers", "llm_model",
)
HARDWARE_FIELDS = (
    "cpu_type", "cpu_freq_mhz", "cpu_cores", "ram_gb", "gpu_model", "vram_gb",
)
FINAL_RESULT_FIELDS = (
    "total_score", "sub_games_won", "ties", "winner_group", "series_tie",
    "tokens_total_series",
)


def _signature(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def _official_group(group: dict) -> dict:
    block = {key: group[key] for key in GROUP_FIELDS}
    hardware = group["hardware_spec"]
    block["hardware_spec"] = {key: hardware.get(key) for key in HARDWARE_FIELDS}
    block["signature"] = _signature(block)
    return block


def official_config_terms(terms: dict) -> dict:
    """Project negotiated runtime terms onto the exact reference config hash scope."""
    projected = {
        "schema_version": SCHEMA_VERSION,
        "_note": terms.get("_note", CONFIG_NOTE),
        "agreed_between": list(terms["agreed_between"]),
    }
    for block, fields in CONFIG_BLOCK_FIELDS.items():
        source = terms[block]
        projected[block] = {field: source[field] for field in fields}
    return projected


def official_final_result(final: dict) -> dict:
    """Whitelist the aggregate fields present in Yoram's result template."""
    return {key: final[key] for key in FINAL_RESULT_FIELDS}


def build_declaration(
    *, game_id: str, game_uid: str, groups: list[dict], num_sub_games: int,
    timezone: str, game_started_at: str, game_ended_at: str, max_tokens_per_game: int,
) -> dict:
    """Build the exact match-level declaration template."""
    if len(groups) != 2:
        raise KitDocumentError(f"a declaration names exactly two groups, got {len(groups)}")
    return {
        "_schema": DECLARATION_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "declaration_type": "pre_game_declaration",
        "game_id": game_id,
        "game_uid": game_uid,
        "links": links_block(game_id),
        "timezone": timezone,
        "game_started_at": game_started_at,
        "game_ended_at": game_ended_at,
        "num_sub_games": num_sub_games,
        "max_tokens_per_game": max_tokens_per_game,
        "groups": {"group_1": _official_group(groups[0]), "group_2": _official_group(groups[1])},
    }


def build_config(*, game_id: str, game_uid: str, sub_game_number: int, terms: dict) -> dict:
    """Build the exact flat config and hash the same field scope as Yoram's builder."""
    shared = official_config_terms(terms)
    return {
        "_schema": CONFIG_SCHEMA,
        **shared,
        "game_id": game_id,
        "game_uid": game_uid,
        "sub_game_number": sub_game_number,
        "links": links_block(game_id),
        "config_name": config_name(game_id, sub_game_number),
        "config_sha256": hashlib.sha256(canonical_bytes(shared)).hexdigest(),
    }


def build_log(*, game_id: str, game_uid: str, summary: dict, records: list[dict]) -> dict:
    """Build one exact Replay Viewer log without internal opponent evidence."""
    checked = check_records(records, "own")
    return {
        "_schema": LOG_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "game_id": game_id,
        "game_uid": game_uid,
        "links": links_block(game_id),
        "summary": summary,
        "records": checked,
        "mutual_agreement": {
            "opponent_group_id": summary["opponent_group_id"],
            "sha256": _signature(checked),
            "confirmed": bool(summary["audit"]["passed"]),
        },
    }


def build_result(
    *, game_id: str, game_uid: str, groups: list[str], sub_games: list[dict],
    final_result: dict, mutual_agreement: dict,
) -> dict:
    """Build the exact six-sub-game result template."""
    return {
        "_schema": RESULT_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "report_type": "final_game_result",
        "game_id": game_id,
        "game_uid": game_uid,
        "links": links_block(game_id),
        "timezone": "Asia/Jerusalem",
        "groups": list(groups),
        "num_sub_games": len(sub_games),
        "sub_games": sub_games,
        "final_result": final_result,
        "mutual_agreement": mutual_agreement,
    }
