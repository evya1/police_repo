from __future__ import annotations

import csv
import os
import sys
import unittest
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

from usage_dashboard_data import DashboardError  # noqa: E402
from usage_dashboard_openrouter import (  # noqa: E402
    EXPECTED_OPENROUTER,
    aggregate_openrouter,
    reconcile_openrouter,
)

HEADER = [
    "generation_id",
    "created_at",
    "cost_total",
    "cost_web_search",
    "cost_cache",
    "cost_file_processing",
    "byok_usage_inference",
    "tokens_prompt",
    "tokens_completion",
    "tokens_reasoning",
    "tokens_cached",
    "model_permaslug",
    "provider_name",
    "variant",
    "cancelled",
    "streamed",
    "user",
    "finish_reason_raw",
    "finish_reason_normalized",
    "generation_time_ms",
    "time_to_first_token_ms",
    "app_name",
    "api_key_name",
    "api_key_disabled",
]
SENTINELS = [
    "SENSITIVE_USER_SENTINEL",
    "SENSITIVE_API_KEY_NAME_SENTINEL",
    "SENSITIVE_GENERATION_ID_SENTINEL",
    "SENSITIVE_APP_NAME_SENTINEL",
    "SENSITIVE_SESSION_ID_SENTINEL",
]


def synthetic_row(
    day: str, model: str, provider: str, cost: str, prompt: str = "10", completion: str = "3"
) -> list[str]:
    values = dict.fromkeys(HEADER, "")
    values.update(
        {
            "generation_id": SENTINELS[2],
            "created_at": f"{day}T12:34:56.123456Z",
            "cost_total": cost,
            "tokens_prompt": prompt,
            "tokens_completion": completion,
            "tokens_reasoning": "2",
            "tokens_cached": "7",
            "model_permaslug": model,
            "provider_name": provider,
            "user": SENTINELS[0],
            "app_name": SENTINELS[3],
            "api_key_name": SENTINELS[1],
        }
    )
    return [values[name] for name in HEADER]


class OpenRouterTests(unittest.TestCase):
    def write_csv(self, directory: str, rows: list[list[str]], header: list[str] = HEADER) -> Path:
        path = Path(directory) / "synthetic.csv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(header)
            writer.writerows(rows)
        return path

    def test_aggregates_date_model_provider_and_decimal_cost(self) -> None:
        with TemporaryDirectory() as directory:
            path = self.write_csv(
                directory,
                [
                    synthetic_row("2026-08-17", "model<a", "provider&one", "1.100001"),
                    synthetic_row("2026-08-17", "model<a", "provider&one", "2.200002"),
                    synthetic_row("2026-08-18", "model-b", "provider-two", "0.300003"),
                ],
            )
            data = aggregate_openrouter(path)
        self.assertEqual(data["requests"], 3)
        self.assertEqual(data["cost"], Decimal("3.600006"))
        self.assertEqual(data["daily"]["2026-08-17"]["model<a"], Decimal("3.300003"))
        self.assertEqual(data["models"]["model<a"]["requests"], 2)
        self.assertEqual(data["models"]["model<a"]["providers"], {"provider&one"})

    def test_missing_and_malformed_input_are_sanitized(self) -> None:
        with TemporaryDirectory() as directory:
            missing = [name for name in HEADER if name != "created_at"]
            path = self.write_csv(directory, [], missing)
            with self.assertRaisesRegex(DashboardError, "invalid OpenRouter input"):
                aggregate_openrouter(path)
            path = self.write_csv(
                directory,
                [
                    synthetic_row(
                        "2026-08-17", "model", "provider", "SENSITIVE_GENERATION_ID_SENTINEL"
                    )
                ],
            )
            with self.assertRaises(DashboardError) as raised:
                aggregate_openrouter(path)
        self.assertNotIn("SENSITIVE", str(raised.exception))

    @unittest.skipUnless(os.environ.get("OPENROUTER_ACTIVITY_CSV"), "private local input not set")
    def test_private_input_reconciles_when_supplied_locally(self) -> None:
        data = aggregate_openrouter(os.environ["OPENROUTER_ACTIVITY_CSV"])
        reconcile_openrouter(data)
        self.assertEqual(data["cost"], EXPECTED_OPENROUTER["cost"])


if __name__ == "__main__":
    unittest.main()
