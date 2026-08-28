#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

from usage_dashboard_codex_extract import aggregate_sessions
from usage_dashboard_codex_pricing import TOKEN_KEYS, sanitized_aggregate
from usage_dashboard_data import DashboardError

BASELINE = {
    "session_count": 14,
    "first_day": "2026-08-24",
    "last_day": "2026-08-25",
    "estimated_cost_usd": "223.7343216",
    "models": {"GPT-5.6 Sol": (14, 9_484_067, 1_466_599, 494_310, 391_165_184, 0)},
    "totals": (9_484_067, 1_466_599, 494_310, 391_165_184, 0),
}


def _baseline(path: str | Path) -> dict[str, object]:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        rows = {
            row["model"]: tuple(row[key] for key in ("session_appearances", *TOKEN_KEYS))
            for row in data["models"]
        }
        totals = tuple(data["totals"][key] for key in TOKEN_KEYS)
        actual = {
            key: data[key] for key in ("session_count", "first_day", "last_day", "estimated_cost_usd")
        }
        actual.update(models=rows, totals=totals)
        if actual != BASELINE:
            raise ValueError
        return data
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        raise DashboardError("Codex baseline reconciliation failed") from None


def append_baseline(baseline: dict[str, object], addition: dict[str, object]) -> dict[str, object]:
    models = defaultdict(lambda: dict.fromkeys((*TOKEN_KEYS, "session_appearances"), 0))
    for source in (baseline, addition):
        for row in source["models"]:
            for key in ("session_appearances", *TOKEN_KEYS):
                models[row["model"]][key] += int(row[key])
    result = sanitized_aggregate(
        models,
        int(baseline["session_count"]) + int(addition["session_count"]),
        min(str(baseline["first_day"]), str(addition["first_day"])),
        max(str(baseline["last_day"]), str(addition["last_day"])),
        int(addition["recorded_duration_ms"]),
        int(addition["duration_session_count"]),
    )
    expected = Decimal(BASELINE["estimated_cost_usd"]) + Decimal(addition["estimated_cost_usd"])
    if Decimal(result["estimated_cost_usd"]) != expected:
        raise DashboardError("Codex baseline reconciliation failed")
    return result


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Create a sanitized Codex usage aggregate.")
    result.add_argument("--session-root", action="append", required=True)
    result.add_argument("--baseline", required=True)
    result.add_argument("--output", required=True)
    return result


def main(argv: list[str] | None = None) -> int:
    try:
        args = parser().parse_args(argv)
        result = append_baseline(_baseline(args.baseline), aggregate_sessions(args.session_root))
        Path(args.output).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    except (OSError, DashboardError):
        print("error: unable to create sanitized Codex aggregate", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
