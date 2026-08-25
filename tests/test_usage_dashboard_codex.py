from __future__ import annotations

import json
import sys
import unittest
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

from usage_dashboard_codex import DashboardError, load_codex  # noqa: E402

SESSION_SENTINEL = "SENSITIVE_CODEX_SESSION_ID_SENTINEL"


class CodexTests(unittest.TestCase):
    aggregate_path = Path(__file__).parents[1] / "data" / "codex-usage-aggregate.json"

    def test_completed_session_tokens_and_estimated_cost_reconcile(self) -> None:
        data = load_codex(self.aggregate_path)
        self.assertEqual(data["session_count"], 14)
        self.assertEqual(data["first_day"], "2026-08-24")
        self.assertEqual(data["last_day"], "2026-08-25")
        self.assertEqual(data["totals"]["input_tokens"], 9_484_067)
        self.assertEqual(data["totals"]["output_tokens"], 1_466_599)
        self.assertEqual(data["totals"]["cache_read_tokens"], 391_165_184)
        self.assertEqual(Decimal(data["estimated_cost_usd"]), Decimal("223.7343216"))

    def test_session_level_data_is_rejected_without_leakage(self) -> None:
        data = json.loads(self.aggregate_path.read_text(encoding="utf-8"))
        data["sessions"] = [{"id": SESSION_SENTINEL}]
        with TemporaryDirectory() as directory:
            path = Path(directory) / "aggregate.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(DashboardError) as raised:
                load_codex(path)
        self.assertNotIn(SESSION_SENTINEL, str(raised.exception))


if __name__ == "__main__":
    unittest.main()
