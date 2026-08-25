#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from decimal import Decimal
from pathlib import Path

from usage_dashboard_data import (
    DashboardError,
    combined_totals,
    load_claude,
)
from usage_dashboard_markdown import render_markdown, update_readme
from usage_dashboard_openrouter import aggregate_openrouter, reconcile_openrouter
from usage_dashboard_svg import render_svg

EXPECTED_COMBINED = {
    "cost": Decimal("451.634392"),
    "input": 309_147_592,
    "output": 3_191_327,
}


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Generate the aggregate AI usage dashboard.")
    result.add_argument("--openrouter-input", required=True)
    result.add_argument("--claude-input", required=True)
    result.add_argument("--output-dir", required=True)
    result.add_argument("--update-readme")
    return result


def run(arguments: argparse.Namespace) -> None:
    openrouter = aggregate_openrouter(arguments.openrouter_input)
    reconcile_openrouter(openrouter)
    claude = load_claude(arguments.claude_input)
    if combined_totals(openrouter, claude) != EXPECTED_COMBINED:
        raise DashboardError("combined reconciliation failed")
    try:
        output = Path(arguments.output_dir)
        output.mkdir(parents=True, exist_ok=True)
        (output / "ai-usage-light.svg").write_text(
            render_svg(openrouter, claude, "light"), encoding="utf-8"
        )
        (output / "ai-usage-dark.svg").write_text(
            render_svg(openrouter, claude, "dark"), encoding="utf-8"
        )
    except OSError:
        raise DashboardError("unable to write dashboard output") from None
    if arguments.update_readme:
        update_readme(arguments.update_readme, render_markdown(openrouter, claude))


def main(argv: list[str] | None = None) -> int:
    try:
        run(parser().parse_args(argv))
    except DashboardError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
