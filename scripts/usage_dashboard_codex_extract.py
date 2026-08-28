from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Iterator
from datetime import date
from pathlib import Path

from usage_dashboard_codex_pricing import TOKEN_KEYS, sanitized_aggregate
from usage_dashboard_data import DashboardError

SOURCE_KEYS = (
    "input_tokens", "output_tokens", "reasoning_output_tokens",
    "cached_input_tokens", "cache_write_input_tokens",
)


def _records(path: Path) -> Iterator[dict[str, object]]:
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            value = json.loads(line)
            values = value if isinstance(value, list) else [value]
            if not all(isinstance(item, dict) for item in values):
                raise ValueError
            yield from values


def _usage(payload: dict[str, object]) -> dict[str, int] | None:
    info = payload.get("info")
    raw = info.get("total_token_usage") if isinstance(info, dict) else None
    if not isinstance(raw, dict):
        return None
    values = {}
    for key in SOURCE_KEYS:
        value = raw.get(key, 0)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError
        values[key] = value
    return values


def _day(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError
    return date.fromisoformat(value[:10]).isoformat()


def _session(path: Path) -> dict[str, object] | None:
    identity = model = None
    current = None
    previous = dict.fromkeys(SOURCE_KEYS, 0)
    models = defaultdict(lambda: dict.fromkeys(TOKEN_KEYS, 0))
    appearances: set[str] = set()
    days: list[str] = []
    latest = ""
    duration = completed = duration_markers = 0
    for record in _records(path):
        payload = record.get("payload")
        if not isinstance(payload, dict):
            continue
        kind = record.get("type")
        if kind == "session_meta" and isinstance(payload.get("id"), str):
            identity = payload["id"]
        elif kind == "turn_context" and isinstance(payload.get("model"), str):
            model = payload["model"]
        elif kind == "event_msg" and payload.get("type") == "token_count":
            current = _usage(payload)
        elif kind == "event_msg" and payload.get("type") == "task_complete":
            if identity is None or model is None or current is None:
                continue
            delta = {key: current[key] - previous[key] for key in SOURCE_KEYS}
            if any(value < 0 for value in delta.values()):
                raise ValueError
            if delta["input_tokens"] < delta["cached_input_tokens"]:
                raise ValueError
            previous = current.copy()
            item = models[model]
            item["input_tokens"] += delta["input_tokens"] - delta["cached_input_tokens"]
            item["output_tokens"] += delta["output_tokens"]
            item["reasoning_output_tokens"] += delta["reasoning_output_tokens"]
            item["cache_read_tokens"] += delta["cached_input_tokens"]
            item["cache_write_tokens"] += delta["cache_write_input_tokens"]
            appearances.add(model)
            marker = record.get("timestamp")
            days.append(_day(marker))
            latest = str(marker)
            completed += 1
            value = payload.get("duration_ms")
            if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
                duration += value
                duration_markers += 1
    if identity is None or not completed:
        return None
    for name in appearances:
        models[name]["session_appearances"] = 1
    return {
        "identity": identity, "models": models, "first": min(days), "last": max(days),
        "latest": latest, "completed": completed, "duration": duration,
        "duration_covered": duration_markers == completed,
    }


def aggregate_sessions(roots: list[str | Path]) -> dict[str, object]:
    try:
        copies = {}
        for root_value in roots:
            root = Path(root_value)
            paths = [root] if root.is_file() else sorted(
                path for path in root.rglob("*") if path.suffix in {".json", ".jsonl"}
            )
            for path in paths:
                candidate = _session(path)
                if candidate is None:
                    continue
                identity = candidate.pop("identity")
                prior = copies.get(identity)
                rank = (candidate["latest"], candidate["completed"])
                if prior is None or rank > (prior["latest"], prior["completed"]):
                    copies[identity] = candidate
        if not copies:
            raise ValueError
        models = defaultdict(lambda: dict.fromkeys((*TOKEN_KEYS, "session_appearances"), 0))
        for session in copies.values():
            for name, values in session["models"].items():
                for key, value in values.items():
                    models[name][key] += value
        first = min(item["first"] for item in copies.values())
        last = max(item["last"] for item in copies.values())
        duration = sum(item["duration"] for item in copies.values())
        covered = sum(bool(item["duration_covered"]) for item in copies.values())
        return sanitized_aggregate(models, len(copies), first, last, duration, covered)
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError):
        raise DashboardError("invalid Codex session input") from None
