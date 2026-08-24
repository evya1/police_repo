from __future__ import annotations

import csv
from collections import defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import TextIO

from usage_dashboard_data import DashboardError, parse_count, parse_money

OPENROUTER_COLUMNS = (
    "created_at",
    "cost_total",
    "tokens_prompt",
    "tokens_completion",
    "tokens_reasoning",
    "tokens_cached",
    "model_permaslug",
    "provider_name",
)
EXPECTED_OPENROUTER = {
    "requests": 4142,
    "cost": Decimal("40.874392"),
    "prompt": 309_121_198,
    "completion": 2_657_111,
    "reasoning": 1_508_969,
    "cached": 268_300_143,
    "first_day": "2026-08-17",
    "last_day": "2026-08-21",
    "model_count": 23,
    "provider_count": 21,
}


def _empty_aggregate() -> dict[str, object]:
    return {
        "requests": 0,
        "cost": Decimal(0),
        "prompt": 0,
        "completion": 0,
        "reasoning": 0,
        "cached": 0,
        "daily": defaultdict(lambda: defaultdict(Decimal)),
        "models": defaultdict(
            lambda: {
                "providers": set(),
                "requests": 0,
                "prompt": 0,
                "completion": 0,
                "cost": Decimal(0),
            }
        ),
        "providers": set(),
    }


def _read_rows(handle: TextIO) -> dict[str, object]:
    result = _empty_aggregate()
    rows = csv.reader(handle)
    header = next(rows)
    if len(header) != len(set(header)) or not set(OPENROUTER_COLUMNS) <= set(header):
        raise DashboardError("invalid OpenRouter schema")
    indexes = {name: header.index(name) for name in OPENROUTER_COLUMNS}
    for row in rows:
        if len(row) != len(header):
            raise DashboardError("invalid OpenRouter input")
        values = {name: row[indexes[name]] for name in OPENROUTER_COLUMNS}
        day = date.fromisoformat(values["created_at"][:10]).isoformat()
        cost = parse_money(values["cost_total"])
        counts = {
            name: parse_count(values[name])
            for name in ("tokens_prompt", "tokens_completion", "tokens_reasoning", "tokens_cached")
        }
        model = values["model_permaslug"].strip() or "Unknown model"
        provider = values["provider_name"].strip() or "Unknown provider"
        result["requests"] += 1
        for key, value in (
            ("cost", cost),
            ("prompt", counts["tokens_prompt"]),
            ("completion", counts["tokens_completion"]),
            ("reasoning", counts["tokens_reasoning"]),
            ("cached", counts["tokens_cached"]),
        ):
            result[key] += value
        result["daily"][day][model] += cost
        item = result["models"][model]
        item["providers"].add(provider)
        item["requests"] += 1
        item["prompt"] += counts["tokens_prompt"]
        item["completion"] += counts["tokens_completion"]
        item["cost"] += cost
        result["providers"].add(provider)
    return result


def aggregate_openrouter(path: str | Path) -> dict[str, object]:
    try:
        with Path(path).open(encoding="utf-8", newline="") as handle:
            return _read_rows(handle)
    except OSError:
        raise DashboardError("unable to read OpenRouter input") from None
    except (csv.Error, UnicodeError, ValueError, IndexError, DashboardError):
        raise DashboardError("invalid OpenRouter input") from None


def reconcile_openrouter(data: dict[str, object]) -> None:
    days = sorted(data["daily"])
    actual = {
        key: data[key]
        for key in ("requests", "cost", "prompt", "completion", "reasoning", "cached")
    }
    actual.update(
        first_day=days[0] if days else "",
        last_day=days[-1] if days else "",
        model_count=len(data["models"]),
        provider_count=len(data["providers"]),
    )
    if actual != EXPECTED_OPENROUTER:
        raise DashboardError("OpenRouter reconciliation failed")
