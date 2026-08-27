from __future__ import annotations

import csv
from collections import defaultdict
from collections.abc import Iterable
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import TextIO

from usage_dashboard_data import DashboardError, parse_count, parse_money

OPENROUTER_COLUMNS = (
    "generation_id",
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
    "requests": 4501,
    "cost": Decimal("44.938573"),
    "prompt": 326_268_002,
    "completion": 2_838_882,
    "reasoning": 1_609_603,
    "cached": 282_377_796,
    "first_day": "2026-08-17",
    "last_day": "2026-08-27",
    "model_count": 26,
    "provider_count": 25,
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


def _read_rows(
    handle: TextIO, result: dict[str, object], seen: dict[str, tuple[object, ...]]
) -> None:
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
        generation_id = values["generation_id"]
        if not generation_id:
            raise DashboardError("invalid OpenRouter input")
        metrics = (day, cost, *counts.values(), model, provider)
        previous = seen.get(generation_id)
        if previous is not None:
            if previous != metrics:
                raise DashboardError("conflicting duplicate OpenRouter record")
            continue
        seen[generation_id] = metrics
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


def aggregate_openrouter(paths: str | Path | Iterable[str | Path]) -> dict[str, object]:
    inputs = [paths] if isinstance(paths, (str, Path)) else list(paths)
    if not inputs:
        raise DashboardError("invalid OpenRouter input")
    result = _empty_aggregate()
    seen: dict[str, tuple[object, ...]] = {}
    try:
        for path in inputs:
            with Path(path).open(encoding="utf-8-sig", newline="") as handle:
                _read_rows(handle, result, seen)
        return result
    except OSError:
        raise DashboardError("unable to read OpenRouter input") from None
    except (csv.Error, UnicodeError, ValueError, IndexError, StopIteration, DashboardError):
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
