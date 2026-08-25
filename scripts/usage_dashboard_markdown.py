from __future__ import annotations

from decimal import ROUND_UP, Decimal
from html import escape

from usage_dashboard_data import combined_totals
from usage_dashboard_markdown_openrouter import model as openrouter_model
from usage_dashboard_markdown_openrouter import model_rows, providers


def _label(value: object) -> str:
    return escape(str(value), quote=True).replace("|", "&#124;")


def _int(value: object) -> str:
    return f"{int(value):,}"


def _money(value: object) -> str:
    return f"${Decimal(str(value)).quantize(Decimal('0.01')):,.2f}"


def render_markdown(
    openrouter: dict[str, object], claude: dict[str, object], codex: dict[str, object]
) -> str:
    combined = combined_totals(openrouter, claude, codex)
    lines = [
        "<!-- generated aggregate data only -->",
        "## AI Usage",
        "",
        "> [!IMPORTANT]",
        f"> ### Total AI / LLM Cost — **{_money(combined['cost'])}**",
        f"> **OpenRouter:** {_money(openrouter['cost'])} · **Claude Code:** {_money(claude['accounted_cost_usd'])} · **Codex:** {_money(codex['estimated_cost_usd'])} estimated",
        ">",
        "> Sanitized aggregate project usage only — no secrets, credentials, personal identifiers, session IDs, request IDs, UUIDs, usernames, or private metadata are published.",
        "",
        "<picture>",
        '  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/ai-usage-dark.svg">',
        '  <source media="(prefers-color-scheme: light)" srcset="docs/assets/ai-usage-light.svg">',
        '  <img alt="Aggregated OpenRouter, Claude Code, and Codex usage and cost" src="docs/assets/ai-usage-light.svg">',
        "</picture>",
        "",
        "This dashboard combines the frozen OpenRouter and Claude Code baseline with a sanitized aggregate of completed Codex sessions. Only aggregate categories and calendar-day buckets are published.",
        "",
        "### Reconciliation",
        "",
        "| Metric | Aggregate |",
        "| --- | ---: |",
        f"| Total AI / LLM cost | **{_money(combined['cost'])}** |",
        f"| OpenRouter reported spend | {_money(openrouter['cost'])} |",
        f"| Claude Code accounted spend | {_money(claude['accounted_cost_usd'])} |",
        f"| Claude Code source-reported spend | {_money(claude['reported_cost_usd'])} |",
        f"| Codex API list-price estimate | {_money(codex['estimated_cost_usd'])} |",
        f"| OpenRouter requests | {_int(openrouter['requests'])} |",
        f"| Claude Code sessions | {_int(claude['session_count'])} |",
        f"| Codex sessions | {_int(codex['session_count'])} |",
        f"| Combined non-cache input / prompt tokens | {_int(combined['input'])} |",
        f"| Combined non-cache output / completion tokens | {_int(combined['output'])} |",
        "",
        f"OpenRouter covers calendar days `2026-08-17` through `2026-08-21`. Codex covers completed session data from `{codex['first_day']}` through `{codex['last_day']}`. No Claude Code date range was inferred. Requests and sessions remain separate activity units.",
        "",
        "### Claude Code model summary",
        "",
        "| Model | Session appearances | Input | Output | Cache read | Cache write | Attributed cost |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for model in claude["models"]:
        lines.append(
            "| {} | {} | {} | {} | {} | {} | ${} |".format(
                _label(model["model"]),
                _int(model["session_appearances"]),
                _int(model["input_tokens"]),
                _int(model["output_tokens"]),
                _int(model["cache_read_tokens"]),
                _int(model["cache_write_tokens"]),
                _label(model["attributed_cost_usd"]),
            )
        )
    lines.extend(
        [
            f"| Unallocated multi-model session | — | — | — | — | — | ${_label(claude['unallocated_multi_model_cost_usd'])} |",
            f"| **Total** | **{_int(claude['session_count'])} sessions** | **{_int(claude['totals']['input_tokens'])}** | **{_int(claude['totals']['output_tokens'])}** | **{_int(claude['totals']['cache_read_tokens'])}** | **{_int(claude['totals']['cache_write_tokens'])}** | **${Decimal(claude['accounted_cost_usd']):.2f}** |",
            "",
            "Opus 4.8 is a $159.56 list-price equivalent calculated from [Anthropic's standard pricing](https://platform.claude.com/docs/en/build-with-claude/prompt-caching): $5/M input, $25/M output, $6.25/M default five-minute cache writes, and $0.50/M cache reads. Other Claude costs remain source-reported.",
            "",
            "Session appearances are not additive because a session may use more than one model. Cache reads and cache writes are reported separately and are not treated as normal input tokens.",
            "",
            "### Codex model summary",
            "",
            "| Model | Session appearances | Non-cache input | Output | Reasoning output | Cache read | Cache write | Estimated cost |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for model in codex["models"]:
        lines.append(
            "| {} | {} | {} | {} | {} | {} | {} | {} |".format(
                _label(model["model"]),
                _int(model["session_appearances"]),
                _int(model["input_tokens"]),
                _int(model["output_tokens"]),
                _int(model["reasoning_output_tokens"]),
                _int(model["cache_read_tokens"]),
                _int(model["cache_write_tokens"]),
                _money(model["attributed_cost_usd"]),
            )
        )
    lines.extend(
        [
            f"| **Total** | **{_int(codex['session_count'])} sessions** | **{_int(codex['totals']['input_tokens'])}** | **{_int(codex['totals']['output_tokens'])}** | **{_int(codex['totals']['reasoning_output_tokens'])}** | **{_int(codex['totals']['cache_read_tokens'])}** | **{_int(codex['totals']['cache_write_tokens'])}** | **{_money(codex['estimated_cost_usd'])}** |",
            "",
            "Codex records do not include billed cost. The estimate uses [OpenAI's GPT-5.6 Sol promotional API pricing](https://developers.openai.com/api/docs/models/gpt-5.6-sol): $4.00/M non-cache input, $0.40/M cached input, $5.00/M cache writes, and $20.00/M output. Reasoning output is included in output and is not charged twice.",
            "",
            "Codex sessions are deduplicated by private session linkage, but only aggregate counts are published. Token counters are taken at each thread's last completion marker; later aborted or incomplete work is excluded.",
            "",
            "### OpenRouter model summary",
            "",
            "| Model | Provider | Requests | Prompt tokens | Completion tokens | Total reported cost | Share of cost |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in model_rows(openrouter):
        share = row["cost"] / openrouter["cost"] * Decimal(100)
        lines.append(
            "| {} | {} | {} | {} | {} | ${} | {:.2f}% |".format(
                openrouter_model(row["model"]),
                providers(row["provider"]),
                _int(row["requests"]),
                _int(row["prompt"]),
                _int(row["completion"]),
                row["cost"].quantize(Decimal("0.01"), rounding=ROUND_UP),
                share,
            )
        )
    lines.extend(
        [
            "",
            "> Claude Code includes four sessions that source-reported $0.00. The Opus 4.8 list-price equivalent is included in accounted spend; one $15.65 multi-model session remains unallocated rather than assigning its cost to a model without evidence.",
            "",
            "> Totals are calculated from full-precision values before public dollar amounts are rounded to two decimal places.",
            "",
            "Regenerate with a private input kept outside the repository:",
            "",
            "```bash",
            "python scripts/generate_usage_dashboard.py \\",
            "  --openrouter-input openrouter_activity.csv \\",
            "  --claude-input data/claude-code-usage-aggregate.json \\",
            "  --codex-input data/codex-usage-aggregate.json \\",
            "  --output-dir docs/assets \\",
            "  --update-readme README.md",
            "```",
        ]
    )
    return "\n".join(lines) + "\n"
