from __future__ import annotations

import json
import sys
import unittest
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

from aggregate_codex_sessions import _baseline, append_baseline  # noqa: E402
from usage_dashboard_codex import DashboardError, load_codex  # noqa: E402
from usage_dashboard_codex_extract import aggregate_sessions  # noqa: E402

PRIVATE = "SENSITIVE_PRIVATE_SESSION_VALUE"
FIELDS = (
    "input_tokens", "cached_input_tokens", "output_tokens",
    "reasoning_output_tokens", "cache_write_input_tokens",
)


def events(identity: str, turns: list[tuple[str, tuple[int, ...], str]], day: int = 26):
    yield {"type": "session_meta", "payload": {"id": identity, "cwd": PRIVATE}}
    for index, (model, counts, status) in enumerate(turns):
        yield {"type": "turn_context", "payload": {"model": model, "summary": PRIVATE}}
        usage = dict(zip(FIELDS, counts, strict=True))
        yield {"type": "event_msg", "payload": {
            "type": "token_count", "info": {"total_token_usage": usage}
        }}
        yield {
            "timestamp": f"2026-08-{day:02d}T12:00:{index:02d}Z",
            "type": "event_msg",
            "payload": {"type": status, "duration_ms": 1000, "reason": PRIVATE},
        }


def write_log(root: Path, name: str, records) -> Path:
    path = root / name
    path.write_text("".join(json.dumps(item) + "\n" for item in records), encoding="utf-8")
    return path


class ExtractorTests(unittest.TestCase):
    aggregate_path = Path(__file__).parents[1] / "data" / "codex-usage-aggregate.json"

    def test_active_archive_duplicate_and_cumulative_last_completion(self) -> None:
        turns = [
            ("gpt-5.6-sol", (100, 80, 10, 4, 0), "task_complete"),
            ("gpt-5.6-sol", (250, 200, 30, 9, 0), "task_complete"),
        ]
        with TemporaryDirectory() as directory:
            root = Path(directory)
            write_log(root, "active.jsonl", events(PRIVATE, turns))
            write_log(root, "archived.jsonl", events(PRIVATE, turns))
            data = aggregate_sessions([root])
        self.assertEqual(data["session_count"], 1)
        self.assertEqual(data["totals"]["input_tokens"], 50)
        self.assertEqual(data["totals"]["cache_read_tokens"], 200)
        self.assertEqual(data["totals"]["output_tokens"], 30)
        self.assertNotIn(PRIVATE, repr(data))

    def test_aborted_and_incomplete_tail_are_excluded(self) -> None:
        turns = [
            ("gpt-5.6-sol", (100, 60, 10, 3, 0), "task_complete"),
            ("gpt-5.6-sol", (900, 600, 90, 30, 0), "turn_aborted"),
        ]
        with TemporaryDirectory() as directory:
            root = Path(directory)
            write_log(root, "session.json", list(events(PRIVATE, turns)))
            data = aggregate_sessions([root])
        self.assertEqual(data["totals"]["input_tokens"], 40)
        self.assertEqual(data["totals"]["output_tokens"], 10)
        self.assertEqual(data["recorded_duration_ms"], 1000)

    def test_multi_model_deltas_and_appearances_once_per_session(self) -> None:
        turns = [
            ("gpt-5.6-sol", (100, 70, 10, 4, 0), "task_complete"),
            ("gpt-5.6-sol", (200, 150, 20, 8, 0), "task_complete"),
            ("gpt-5.6-luna", (260, 190, 26, 10, 0), "task_complete"),
        ]
        with TemporaryDirectory() as directory:
            root = Path(directory)
            write_log(root, "multi.jsonl", events(PRIVATE, turns))
            data = aggregate_sessions([root])
        rows = {row["model"]: row for row in data["models"]}
        self.assertEqual(rows["GPT-5.6 Sol"]["session_appearances"], 1)
        self.assertEqual(rows["GPT-5.6 Luna"]["session_appearances"], 1)
        self.assertEqual(rows["GPT-5.6 Luna"]["input_tokens"], 20)
        self.assertEqual(data["session_count"], 1)

    def test_reasoning_is_subset_and_decimal_cost_is_exact(self) -> None:
        turns = [("gpt-5.6-sol", (1_100_000, 100_000, 200_000, 50_000, 0), "task_complete")]
        with TemporaryDirectory() as directory:
            root = Path(directory)
            write_log(root, "cost.jsonl", events(PRIVATE, turns))
            data = aggregate_sessions([root])
        self.assertEqual(data["totals"]["reasoning_output_tokens"], 50_000)
        self.assertEqual(Decimal(data["estimated_cost_usd"]), Decimal("8.04"))

    def test_unknown_model_is_unpriced(self) -> None:
        turns = [("unknown-model", (100, 20, 10, 5, 0), "task_complete")]
        with TemporaryDirectory() as directory:
            root = Path(directory)
            write_log(root, "unknown.jsonl", events(PRIVATE, turns))
            data = aggregate_sessions([root])
        self.assertEqual(data["unpriced_model_count"], 1)
        self.assertIsNone(data["models"][0]["attributed_cost_usd"])
        self.assertEqual(data["estimated_cost_usd"], "0")

    def test_malformed_failure_is_generic(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / f"{PRIVATE}.jsonl"
            path.write_text("{private malformed", encoding="utf-8")
            with self.assertRaises(DashboardError) as raised:
                aggregate_sessions([path])
        self.assertEqual(str(raised.exception), "invalid Codex session input")
        self.assertNotIn(PRIVATE, str(raised.exception))

    def test_exact_baseline_is_preserved_when_appending_continuation(self) -> None:
        turns = [("gpt-5.6-luna", (100, 20, 10, 2, 0), "task_complete")]
        with TemporaryDirectory() as directory:
            root = Path(directory)
            baseline_path = root / "baseline.json"
            baseline_path.write_text(json.dumps({
                "session_count": 14, "first_day": "2026-08-24", "last_day": "2026-08-25",
                "estimated_cost_usd": "223.7343216",
                "models": [{
                    "model": "GPT-5.6 Sol", "session_appearances": 14,
                    "input_tokens": 9_484_067, "output_tokens": 1_466_599,
                    "reasoning_output_tokens": 494_310, "cache_read_tokens": 391_165_184,
                    "cache_write_tokens": 0, "attributed_cost_usd": "223.7343216",
                }],
                "totals": {
                    "input_tokens": 9_484_067, "output_tokens": 1_466_599,
                    "reasoning_output_tokens": 494_310, "cache_read_tokens": 391_165_184,
                    "cache_write_tokens": 0,
                },
            }), encoding="utf-8")
            baseline = _baseline(baseline_path)
            write_log(root, "continued.jsonl", events(PRIVATE, turns, 27))
            merged = append_baseline(baseline, aggregate_sessions([root / "continued.jsonl"]))
        self.assertEqual(merged["session_count"], 15)
        self.assertEqual(merged["totals"]["input_tokens"], 9_484_147)
        sol = next(row for row in merged["models"] if row["model"] == "GPT-5.6 Sol")
        self.assertEqual(sol["input_tokens"], 9_484_067)
        self.assertEqual(sol["attributed_cost_usd"], "223.7343216")

    def test_final_aggregate_reconciles(self) -> None:
        data = load_codex(self.aggregate_path)
        self.assertEqual(data["session_count"], 29)
        self.assertEqual(data["totals"]["input_tokens"], 19_116_435)
        self.assertEqual(data["totals"]["output_tokens"], 2_591_356)
        self.assertEqual(data["totals"]["cache_read_tokens"], 686_603_904)
        self.assertEqual(Decimal(data["estimated_cost_usd"]), Decimal("378.51721144"))


if __name__ == "__main__":
    unittest.main()
