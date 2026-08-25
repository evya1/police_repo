from __future__ import annotations

import json
import sys
import unittest
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

from usage_dashboard_data import DashboardError, combined_totals, load_claude  # noqa: E402

SESSION_SENTINEL = "SENSITIVE_SESSION_ID_SENTINEL"


class ClaudeTests(unittest.TestCase):
    aggregate_path = Path(__file__).parents[1] / "data" / "claude-code-usage-aggregate.json"

    def test_aggregate_and_unallocated_cost_reconcile(self) -> None:
        data = load_claude(self.aggregate_path)
        attributed = sum(
            (Decimal(item["attributed_cost_usd"]) for item in data["models"]), Decimal(0)
        )
        self.assertEqual(attributed, Decimal("395.11"))
        self.assertEqual(
            attributed + Decimal(data["unallocated_multi_model_cost_usd"]), Decimal("410.76")
        )

    def test_repeated_summary_cannot_increase_deduplicated_session_count(self) -> None:
        data = load_claude(self.aggregate_path)
        self.assertEqual(
            (data["session_count"], data["reported_cost_usd"], data["accounted_cost_usd"]),
            (18, "251.20", "410.76"),
        )
        data["session_count"] = 19
        with TemporaryDirectory() as directory:
            path = Path(directory) / "aggregate.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(DashboardError):
                load_claude(path)

    def test_session_level_data_is_rejected_without_leakage(self) -> None:
        data = json.loads(self.aggregate_path.read_text(encoding="utf-8"))
        data["sessions"] = [{"id": SESSION_SENTINEL}]
        with TemporaryDirectory() as directory:
            path = Path(directory) / "aggregate.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(DashboardError) as raised:
                load_claude(path)
        self.assertNotIn(SESSION_SENTINEL, str(raised.exception))

    def test_combined_totals(self) -> None:
        claude = load_claude(self.aggregate_path)
        openrouter = {"cost": Decimal("40.874392"), "prompt": 309_121_198, "completion": 2_657_111}
        self.assertEqual(
            combined_totals(openrouter, claude),
            {"cost": Decimal("451.634392"), "input": 309_147_592, "output": 3_191_327},
        )
        self.assertEqual(Decimal("451.634392").quantize(Decimal("0.01")), Decimal("451.63"))


if __name__ == "__main__":
    unittest.main()
