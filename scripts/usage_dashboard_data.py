from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from pathlib import Path


class DashboardError(Exception):
    """A deliberately sanitized dashboard-generation failure."""


CLAUDE_KEYS = {
    "source",
    "session_count",
    "reported_cost_usd",
    "reported_api_time_seconds",
    "reported_wall_time_seconds",
    "zero_reported_cost_sessions",
    "models",
    "unallocated_multi_model_cost_usd",
    "totals",
}
MODEL_KEYS = {
    "model",
    "session_appearances",
    "input_tokens",
    "output_tokens",
    "cache_read_tokens",
    "cache_write_tokens",
    "attributed_reported_cost_usd",
}
TOTAL_KEYS = {"input_tokens", "output_tokens", "cache_read_tokens", "cache_write_tokens"}


def parse_money(value: object) -> Decimal:
    try:
        parsed = Decimal(str(value or "0"))
    except (InvalidOperation, ValueError):
        raise DashboardError("invalid aggregate input") from None
    if not parsed.is_finite() or parsed < 0:
        raise DashboardError("invalid aggregate input")
    return parsed


def parse_count(value: object) -> int:
    if isinstance(value, bool):
        raise DashboardError("invalid aggregate input")
    try:
        parsed = int(str(value or "0"))
    except ValueError:
        raise DashboardError("invalid aggregate input") from None
    if parsed < 0:
        raise DashboardError("invalid aggregate input")
    return parsed


def load_claude(path: str | Path) -> dict[str, object]:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(data, dict) or set(data) != CLAUDE_KEYS:
            raise DashboardError("invalid Claude aggregate input")
        if data["source"] != "Claude Code" or not isinstance(data["models"], list):
            raise DashboardError("invalid Claude aggregate input")
        if not isinstance(data["totals"], dict) or set(data["totals"]) != TOTAL_KEYS:
            raise DashboardError("invalid Claude aggregate input")
        attributed = Decimal(0)
        summed = dict.fromkeys(TOTAL_KEYS, 0)
        for model in data["models"]:
            if not isinstance(model, dict) or set(model) != MODEL_KEYS:
                raise DashboardError("invalid Claude aggregate input")
            attributed += parse_money(model["attributed_reported_cost_usd"])
            for key in TOTAL_KEYS:
                summed[key] += parse_count(model[key])
        expected = {key: parse_count(data["totals"][key]) for key in TOTAL_KEYS}
        total = parse_money(data["reported_cost_usd"])
        unallocated = parse_money(data["unallocated_multi_model_cost_usd"])
        if summed != expected or attributed + unallocated != total:
            raise DashboardError("Claude reconciliation failed")
        if total != Decimal("251.20") or parse_count(data["session_count"]) != 18:
            raise DashboardError("Claude reconciliation failed")
        if parse_count(data["zero_reported_cost_sessions"]) != 4:
            raise DashboardError("Claude reconciliation failed")
        return data
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError, DashboardError):
        raise DashboardError("invalid Claude aggregate input") from None


def combined_totals(openrouter: dict[str, object], claude: dict[str, object]) -> dict[str, object]:
    return {
        "cost": openrouter["cost"] + parse_money(claude["reported_cost_usd"]),
        "input": openrouter["prompt"] + parse_count(claude["totals"]["input_tokens"]),
        "output": openrouter["completion"] + parse_count(claude["totals"]["output_tokens"]),
    }
