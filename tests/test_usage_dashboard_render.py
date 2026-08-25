from __future__ import annotations

import io
import re
import sys
import unittest
from collections import defaultdict
from contextlib import redirect_stderr
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from xml.etree import ElementTree

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

from generate_usage_dashboard import main  # noqa: E402
from usage_dashboard_codex import load_codex  # noqa: E402
from usage_dashboard_data import load_claude  # noqa: E402
from usage_dashboard_markdown import render_markdown  # noqa: E402
from usage_dashboard_markdown_update import update_readme  # noqa: E402
from usage_dashboard_svg import render_svg  # noqa: E402

SENTINELS = (
    "SENSITIVE_USER_SENTINEL",
    "SENSITIVE_API_KEY_NAME_SENTINEL",
    "SENSITIVE_GENERATION_ID_SENTINEL",
    "SENSITIVE_APP_NAME_SENTINEL",
    "SENSITIVE_SESSION_ID_SENTINEL",
)
EXACT_TIMESTAMP = "2026-08-17T12:34:56.123456Z"


def aggregate() -> dict[str, object]:
    daily: defaultdict[str, defaultdict[str, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
    models: dict[str, dict[str, object]] = {}
    total = Decimal(0)
    for index in range(10):
        name = "vendor/model<unsafe&" if index == 0 else f"vendor/model-{index}"
        provider = "provider|unsafe>" if index == 0 else f"provider-{index}"
        cost = Decimal(10 - index) / Decimal(10)
        day = f"2026-08-{17 + index % 5:02d}"
        daily[day][name] += cost
        models[name] = {
            "providers": {provider},
            "requests": index + 1,
            "prompt": (index + 1) * 10,
            "completion": index + 1,
            "cost": cost,
        }
        total += cost
    return {
        "requests": 55,
        "cost": total,
        "prompt": 550,
        "completion": 55,
        "reasoning": 20,
        "cached": 300,
        "daily": daily,
        "models": models,
        "providers": {f"provider-{index}" for index in range(10)},
    }


class RenderingTests(unittest.TestCase):
    claude_path = Path(__file__).parents[1] / "data" / "claude-code-usage-aggregate.json"
    codex_path = Path(__file__).parents[1] / "data" / "codex-usage-aggregate.json"

    def setUp(self) -> None:
        self.openrouter = aggregate()
        self.claude = load_claude(self.claude_path)
        self.codex = load_codex(self.codex_path)

    def test_svg_is_deterministic_valid_and_theme_specific(self) -> None:
        light = render_svg(self.openrouter, self.claude, self.codex, "light")
        dark = render_svg(self.openrouter, self.claude, self.codex, "dark")
        self.assertEqual(light, render_svg(self.openrouter, self.claude, self.codex, "light"))
        ElementTree.fromstring(light)
        ElementTree.fromstring(dark)
        self.assertNotEqual(light, dark)
        self.assertIn("#F5F7FB", light)
        self.assertIn("#10131A", dark)

    def test_xml_and_markdown_escape_labels_and_group_other(self) -> None:
        svg = render_svg(self.openrouter, self.claude, self.codex, "light")
        markdown = render_markdown(self.openrouter, self.claude, self.codex)
        self.assertIn("model&lt;unsafe&amp;", svg)
        self.assertNotIn("model<unsafe&", svg)
        self.assertIn("model&lt;unsafe&amp;", markdown)
        self.assertIn("provider&#124;unsafe&gt;", markdown)
        self.assertIn("Other (2 models)", markdown)
        self.assertIn(">Other</text>", svg)

    def test_openrouter_model_and_provider_presentation_is_linked(self) -> None:
        item = self.openrouter["models"].pop("vendor/model<unsafe&")
        item["providers"] = {"Baidu", "Google", "Novita"}
        self.openrouter["models"]["z-ai/glm-5.2-20260616"] = item
        markdown = render_markdown(self.openrouter, self.claude, self.codex)
        self.assertIn("[Z.ai: GLM 5.2](https://openrouter.ai/z-ai/glm-5.2)", markdown)
        self.assertIn('href="https://openrouter.ai/provider/baidu"', markdown)
        self.assertIn('src="docs/assets/providers/baidu.png"', markdown)
        self.assertIn("Baidu Qianfan</a>, Google,", markdown)
        self.assertIn("NovitaAI</a>", markdown)
        self.assertNotIn("openrouter.ai/provider/google-", markdown)

    def test_outputs_exclude_timestamps_sensitive_values_and_paths(self) -> None:
        outputs = render_svg(self.openrouter, self.claude, self.codex, "light") + render_markdown(
            self.openrouter, self.claude, self.codex
        )
        self.assertNotIn(EXACT_TIMESTAMP, outputs)
        self.assertNotIn(str(Path.home()), outputs)
        for sentinel in SENTINELS:
            self.assertNotIn(sentinel, outputs)

    def test_public_costs_have_at_most_two_decimal_places(self) -> None:
        outputs = render_svg(self.openrouter, self.claude, self.codex, "light") + render_markdown(
            self.openrouter, self.claude, self.codex
        )
        self.assertEqual(re.findall(r"\$[\d,]+\.\d{3,}", outputs), [])
        self.assertIn("### Total AI / LLM Cost — **$639.99**", outputs)
        self.assertIn("| Total AI / LLM cost | **$639.99** |", outputs)

    def test_readme_update_changes_only_marker_content(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "README.md"
            path.write_text(
                "before\n<!-- ai-usage:start -->\nold\n<!-- ai-usage:end -->\nafter\n",
                encoding="utf-8",
            )
            update_readme(path, "new\n")
            self.assertEqual(
                path.read_text(encoding="utf-8"),
                "before\n<!-- ai-usage:start -->\nnew\n<!-- ai-usage:end -->\nafter\n",
            )

    def test_cli_failure_is_sanitized(self) -> None:
        sensitive_path = "/does-not-exist/SENSITIVE_API_KEY_NAME_SENTINEL.csv"
        errors = io.StringIO()
        with redirect_stderr(errors):
            status = main(
                [
                    "--openrouter-input",
                    sensitive_path,
                    "--claude-input",
                    str(self.claude_path),
                    "--codex-input",
                    str(self.codex_path),
                    "--output-dir",
                    "/unused-output",
                ]
            )
        self.assertEqual(status, 1)
        self.assertEqual(errors.getvalue(), "error: unable to read OpenRouter input\n")
        for sentinel in SENTINELS:
            self.assertNotIn(sentinel, errors.getvalue())


if __name__ == "__main__":
    unittest.main()
