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
    "tokens_prompt",
    "tokens_completion",
    "tokens_reasoning",
    "tokens_cached",
    "model_permaslug",
    "provider_name",
    "user",
    "app_name",
    "api_key_name",
    "request_id",
    "session_id",
    "credential",
]
SENSITIVE = {
    "user": "SENSITIVE_USER_SENTINEL",
    "app_name": "SENSITIVE_APP_NAME_SENTINEL",
    "api_key_name": "SENSITIVE_API_KEY_NAME_SENTINEL",
    "request_id": "SENSITIVE_REQUEST_ID_SENTINEL",
    "session_id": "SENSITIVE_SESSION_ID_SENTINEL",
    "credential": "SENSITIVE_CREDENTIAL_SENTINEL",
}
EXACT_TIMESTAMP = "2026-08-17T12:34:56.123456Z"


def synthetic_row(
    generation_id: str,
    day: str = "2026-08-17",
    model: str = "model-a",
    provider: str = "provider-one",
    cost: str = "1.100001",
) -> dict[str, str]:
    return {
        **dict.fromkeys(HEADER, ""),
        **SENSITIVE,
        "generation_id": generation_id,
        "created_at": EXACT_TIMESTAMP.replace("2026-08-17", day),
        "cost_total": cost,
        "tokens_prompt": "10",
        "tokens_completion": "3",
        "tokens_reasoning": "2",
        "tokens_cached": "7",
        "model_permaslug": model,
        "provider_name": provider,
    }


class OpenRouterTests(unittest.TestCase):
    def write_csv(
        self,
        directory: str,
        name: str,
        rows: list[dict[str, str]],
        header: list[str] = HEADER,
        encoding: str = "utf-8",
    ) -> Path:
        path = Path(directory) / name
        with path.open("w", encoding=encoding, newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=header, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        return path

    def test_aggregates_multiple_csvs_without_sensitive_values(self) -> None:
        with TemporaryDirectory() as directory:
            first = self.write_csv(
                directory,
                "first.csv",
                [synthetic_row("generation-one", model="model<a", provider="provider&one")],
                encoding="utf-8-sig",
            )
            second = self.write_csv(
                directory,
                "second.csv",
                [synthetic_row("generation-two", "2026-08-18", "model-b", "provider-two", "0.300003")],
            )
            data = aggregate_openrouter([first, second])
            rendered = repr(data)
        self.assertEqual(data["requests"], 2)
        self.assertEqual(data["cost"], Decimal("1.400004"))
        self.assertEqual(data["daily"]["2026-08-17"]["model<a"], Decimal("1.100001"))
        self.assertNotIn(EXACT_TIMESTAMP, rendered)
        self.assertNotIn(str(first), rendered)
        for value in [*SENSITIVE.values(), "generation-one", "generation-two"]:
            self.assertNotIn(value, rendered)

    def test_identical_duplicate_id_is_counted_once(self) -> None:
        with TemporaryDirectory() as directory:
            row = synthetic_row("SENSITIVE_GENERATION_ID_SENTINEL")
            duplicate = {**row, "user": "DIFFERENT_PRIVATE_USER"}
            first = self.write_csv(directory, "first.csv", [row])
            second = self.write_csv(directory, "second.csv", [duplicate])
            data = aggregate_openrouter([first, second])
        self.assertEqual((data["requests"], data["cost"]), (1, Decimal("1.100001")))

    def test_conflicting_duplicate_id_is_rejected_without_leakage(self) -> None:
        with TemporaryDirectory() as directory:
            first = self.write_csv(
                directory, "first.csv", [synthetic_row("SENSITIVE_GENERATION_ID_SENTINEL")]
            )
            second = self.write_csv(
                directory,
                "second.csv",
                [synthetic_row("SENSITIVE_GENERATION_ID_SENTINEL", cost="9.900009")],
            )
            with self.assertRaises(DashboardError) as raised:
                aggregate_openrouter([first, second])
        self.assertEqual(str(raised.exception), "invalid OpenRouter input")
        self.assertNotIn("SENSITIVE", str(raised.exception))
        self.assertNotIn("9.900009", str(raised.exception))

    def test_missing_and_malformed_input_are_sanitized(self) -> None:
        with TemporaryDirectory() as directory:
            missing = [name for name in HEADER if name != "created_at"]
            path = self.write_csv(directory, "missing.csv", [], missing)
            with self.assertRaisesRegex(DashboardError, "invalid OpenRouter input"):
                aggregate_openrouter(path)
            path = self.write_csv(
                directory, "malformed.csv", [synthetic_row("generation-three", cost="PRIVATE")]
            )
            with self.assertRaises(DashboardError) as raised:
                aggregate_openrouter(path)
        self.assertEqual(str(raised.exception), "invalid OpenRouter input")
        self.assertNotIn("PRIVATE", str(raised.exception))

    @unittest.skipUnless(os.environ.get("OPENROUTER_ACTIVITY_CSV"), "private local input not set")
    def test_private_inputs_reconcile_when_supplied_locally(self) -> None:
        paths = os.environ["OPENROUTER_ACTIVITY_CSV"].split(os.pathsep)
        self.assertEqual(len(paths), 2)
        baseline = aggregate_openrouter(paths[:1])
        increment = aggregate_openrouter(paths[1:])
        combined = aggregate_openrouter(paths)
        reconcile_openrouter(combined)
        self.assertEqual((baseline["requests"], baseline["cost"]), (4142, Decimal("40.874392")))
        self.assertEqual((increment["requests"], increment["cost"]), (359, Decimal("4.064181")))
        for key, value in EXPECTED_OPENROUTER.items():
            if key in combined:
                self.assertEqual(combined[key], value)


if __name__ == "__main__":
    unittest.main()
