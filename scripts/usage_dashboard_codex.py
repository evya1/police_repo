from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

from usage_dashboard_codex_pricing import RATE_KEYS, TOKEN_KEYS, token_cost
from usage_dashboard_data import MODEL_KEYS, DashboardError, parse_count, parse_money

CODEX_KEYS = {
    "source", "session_count", "first_day", "last_day", "cost_method", "pricing",
    "models", "totals", "estimated_cost_usd", "unpriced_model_count",
    "recorded_duration_ms", "duration_session_count",
}
MODEL_FIELDS = MODEL_KEYS | {"reasoning_output_tokens"}


def _rates(value: object) -> dict[str, str | None]:
    if not isinstance(value, dict) or set(value) != set(RATE_KEYS):
        raise DashboardError("invalid Codex aggregate input")
    result = {}
    for key in RATE_KEYS:
        item = value[key]
        result[key] = None if item is None else str(parse_money(item))
    return result


def load_codex(path: str | Path) -> dict[str, object]:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(data, dict) or set(data) != CODEX_KEYS:
            raise DashboardError("invalid Codex aggregate input")
        if data["source"] != "Codex" or data["cost_method"] != "estimated_api_list_price":
            raise DashboardError("invalid Codex aggregate input")
        first = date.fromisoformat(str(data["first_day"]))
        last = date.fromisoformat(str(data["last_day"]))
        if first > last or not isinstance(data["models"], list):
            raise DashboardError("Codex reconciliation failed")
        if not isinstance(data["pricing"], dict) or not isinstance(data["totals"], dict):
            raise DashboardError("invalid Codex aggregate input")
        if set(data["totals"]) != set(TOKEN_KEYS):
            raise DashboardError("invalid Codex aggregate input")
        session_count = parse_count(data["session_count"])
        duration_sessions = parse_count(data["duration_session_count"])
        if duration_sessions > session_count:
            raise DashboardError("Codex reconciliation failed")
        parse_count(data["recorded_duration_ms"])
        summed = dict.fromkeys(TOKEN_KEYS, 0)
        total_cost = Decimal(0)
        unpriced = 0
        labels = set()
        appearances = 0
        for model in data["models"]:
            if not isinstance(model, dict) or set(model) != MODEL_FIELDS:
                raise DashboardError("invalid Codex aggregate input")
            label = model["model"]
            if not isinstance(label, str) or not label or label in labels:
                raise DashboardError("invalid Codex aggregate input")
            labels.add(label)
            count = parse_count(model["session_appearances"])
            if count > session_count:
                raise DashboardError("Codex reconciliation failed")
            appearances += count
            tokens = {key: parse_count(model[key]) for key in TOKEN_KEYS}
            for key, value in tokens.items():
                summed[key] += value
            rates = _rates(data["pricing"].get(label))
            expected = token_cost(tokens, rates)
            attributed = model["attributed_cost_usd"]
            if expected is None:
                if attributed is not None:
                    raise DashboardError("Codex reconciliation failed")
                unpriced += 1
            else:
                if parse_money(attributed) != expected:
                    raise DashboardError("Codex reconciliation failed")
                total_cost += expected
        expected_totals = {key: parse_count(data["totals"][key]) for key in TOKEN_KEYS}
        if set(data["pricing"]) != labels or summed != expected_totals:
            raise DashboardError("Codex reconciliation failed")
        if appearances < session_count or unpriced != parse_count(data["unpriced_model_count"]):
            raise DashboardError("Codex reconciliation failed")
        if total_cost != parse_money(data["estimated_cost_usd"]):
            raise DashboardError("Codex reconciliation failed")
        return data
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError, DashboardError):
        raise DashboardError("invalid Codex aggregate input") from None
