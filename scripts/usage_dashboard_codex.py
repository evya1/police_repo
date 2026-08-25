from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

from usage_dashboard_data import MODEL_KEYS, TOTAL_KEYS, DashboardError, parse_count, parse_money

CODEX_KEYS = {
    "source",
    "session_count",
    "first_day",
    "last_day",
    "cost_method",
    "pricing",
    "models",
    "totals",
    "estimated_cost_usd",
}
CODEX_MODEL_KEYS = MODEL_KEYS | {"reasoning_output_tokens"}
CODEX_PRICING_KEYS = {
    "input_per_million_usd",
    "cached_input_per_million_usd",
    "cache_write_per_million_usd",
    "output_per_million_usd",
}
CODEX_TOTAL_KEYS = TOTAL_KEYS | {"reasoning_output_tokens"}


def _estimated_cost(totals: dict[str, int], rates: dict[str, Decimal]) -> Decimal:
    return (
        Decimal(totals["input_tokens"]) * rates["input_per_million_usd"]
        + Decimal(totals["cache_read_tokens"]) * rates["cached_input_per_million_usd"]
        + Decimal(totals["cache_write_tokens"]) * rates["cache_write_per_million_usd"]
        + Decimal(totals["output_tokens"]) * rates["output_per_million_usd"]
    ) / Decimal(1_000_000)


def load_codex(path: str | Path) -> dict[str, object]:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(data, dict) or set(data) != CODEX_KEYS:
            raise DashboardError("invalid Codex aggregate input")
        if data["source"] != "Codex" or not isinstance(data["models"], list):
            raise DashboardError("invalid Codex aggregate input")
        if not isinstance(data["pricing"], dict) or set(data["pricing"]) != CODEX_PRICING_KEYS:
            raise DashboardError("invalid Codex aggregate input")
        if not isinstance(data["totals"], dict) or set(data["totals"]) != CODEX_TOTAL_KEYS:
            raise DashboardError("invalid Codex aggregate input")
        first_day = date.fromisoformat(str(data["first_day"]))
        last_day = date.fromisoformat(str(data["last_day"]))
        if first_day > last_day or data["cost_method"] != "estimated_api_list_price":
            raise DashboardError("Codex reconciliation failed")
        summed = dict.fromkeys(CODEX_TOTAL_KEYS, 0)
        appearances = 0
        attributed = Decimal(0)
        for model in data["models"]:
            if not isinstance(model, dict) or set(model) != CODEX_MODEL_KEYS:
                raise DashboardError("invalid Codex aggregate input")
            appearances += parse_count(model["session_appearances"])
            attributed += parse_money(model["attributed_cost_usd"])
            for key in CODEX_TOTAL_KEYS:
                summed[key] += parse_count(model[key])
        expected = {key: parse_count(data["totals"][key]) for key in CODEX_TOTAL_KEYS}
        rates = {key: parse_money(data["pricing"][key]) for key in CODEX_PRICING_KEYS}
        estimated = parse_money(data["estimated_cost_usd"])
        if (
            summed != expected
            or attributed != estimated
            or _estimated_cost(expected, rates) != estimated
        ):
            raise DashboardError("Codex reconciliation failed")
        if appearances != parse_count(data["session_count"]):
            raise DashboardError("Codex reconciliation failed")
        return data
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError, DashboardError):
        raise DashboardError("invalid Codex aggregate input") from None
