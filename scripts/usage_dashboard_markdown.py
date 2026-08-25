from __future__ import annotations

from decimal import ROUND_UP, Decimal
from html import escape
from pathlib import Path

from usage_dashboard_data import DashboardError, combined_totals

START = "<!-- ai-usage:start -->"
END = "<!-- ai-usage:end -->"

MODEL_LINKS = {
    "google/gemini-3.7-flash-20260813": ("Google: Gemini 3.7 Flash", "google/gemini-3.7-flash"), "z-ai/glm-5.2-20260616": ("Z.ai: GLM 5.2", "z-ai/glm-5.2"),
    "deepseek/deepseek-v4-pro-20260813": ("DeepSeek: DeepSeek V4 Pro 0813", "deepseek/deepseek-v4-pro-0813"), "google/gemini-3.1-pro-preview-20260219": ("Google: Gemini 3.1 Pro Preview", "google/gemini-3.1-pro-preview"),
    "deepseek/deepseek-v4-pro-20260423": ("DeepSeek: DeepSeek V4 Pro 0423", "deepseek/deepseek-v4-pro"), "google/gemini-2.5-pro": ("Google: Gemini 2.5 Pro", "google/gemini-2.5-pro"),
    "deepseek/deepseek-v4-flash-20260731": ("DeepSeek: DeepSeek V4 Flash 0731", "deepseek/deepseek-v4-flash-0731"), "moonshotai/kimi-k2.6-20260420": ("MoonshotAI: Kimi K2.6", "moonshotai/kimi-k2.6"),
}

PROVIDERS = frozenset({"Baidu", "Crusoe", "Decart", "Friendli", "GMICloud", "Novita", "SiliconFlow", "StreamLake", "Alibaba", "Parasail", "Together", "DigitalOcean", "Fireworks", "Morph", "Relace"})
PROVIDER_DISPLAY = {"Baidu": "Baidu Qianfan", "Novita": "NovitaAI", "Alibaba": "Alibaba Cloud Int."}
PROVIDER_EXTENSIONS = {"SiliconFlow": "svg", "Morph": "jpg"}


def _label(value: object) -> str:
    return escape(str(value), quote=True).replace("|", "&#124;")


def _int(value: object) -> str:
    return f"{int(value):,}"


def _model(value: object) -> str:
    link = MODEL_LINKS.get(str(value))
    return _label(value) if link is None else f"[{link[0]}](https://openrouter.ai/{link[1]})"


def _provider(value: object) -> str:
    name = str(value)
    if name not in PROVIDERS:
        return _label(value)
    slug = name.lower()
    return f'<a href="https://openrouter.ai/provider/{slug}"><img src="docs/assets/providers/{slug}.{PROVIDER_EXTENSIONS.get(name, "png")}" width="16" alt=""> {PROVIDER_DISPLAY.get(name, name)}</a>'


def _providers(value: object) -> str:
    return ", ".join(_provider(provider) for provider in value) if isinstance(value, list) else _label(value)


def _model_rows(openrouter: dict[str, object], limit: int = 8) -> list[dict[str, object]]:
    ranked = sorted(openrouter["models"].items(), key=lambda item: (-item[1]["cost"], item[0]))
    rows: list[dict[str, object]] = []
    for model, item in ranked[:limit]:
        rows.append({"model": model, "provider": sorted(item["providers"]), **item})
    remainder = ranked[limit:]
    if remainder:
        rows.append(
            {
                "model": f"Other ({len(remainder)} models)",
                "provider": "Multiple providers",
                "requests": sum(item["requests"] for _, item in remainder),
                "prompt": sum(item["prompt"] for _, item in remainder),
                "completion": sum(item["completion"] for _, item in remainder),
                "cost": sum((item["cost"] for _, item in remainder), Decimal(0)),
            }
        )
    return rows


def render_markdown(openrouter: dict[str, object], claude: dict[str, object]) -> str:
    combined = combined_totals(openrouter, claude)
    lines = [
        "<!-- generated aggregate data only -->",
        "## AI Usage",
        "",
        "This dashboard combines private-input OpenRouter activity with a committed, sanitized Claude Code aggregate. Only aggregate categories and calendar-day buckets are published.",
        "",
        "<picture>",
        '  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/ai-usage-dark.svg">',
        '  <source media="(prefers-color-scheme: light)" srcset="docs/assets/ai-usage-light.svg">',
        '  <img alt="Aggregated OpenRouter and Claude Code usage and reported cost" src="docs/assets/ai-usage-light.svg">',
        "</picture>",
        "",
        "### Reconciliation",
        "",
        "| Metric | Aggregate |",
        "| --- | ---: |",
        f"| Combined reported spend | **${combined['cost'].quantize(Decimal('0.01')):,.2f}** (`${combined['cost']}` reconciled) |",
        f"| OpenRouter reported spend | ${openrouter['cost']} |",
        f"| Claude Code reported spend | ${Decimal(claude['reported_cost_usd']):.2f} |",
        f"| OpenRouter requests | {_int(openrouter['requests'])} |",
        f"| Claude Code sessions | {_int(claude['session_count'])} |",
        f"| Combined non-cache input / prompt tokens | {_int(combined['input'])} |",
        f"| Combined non-cache output / completion tokens | {_int(combined['output'])} |",
        "",
        "OpenRouter covers calendar days `2026-08-17` through `2026-08-21`. No Claude Code date range was inferred. Requests and sessions remain separate activity units.",
        "",
        "### Claude Code model summary",
        "",
        "| Model | Session appearances | Input | Output | Cache read | Cache write | Attributed reported cost |",
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
                _label(model["attributed_reported_cost_usd"]),
            )
        )
    lines.extend(
        [
            f"| Unallocated multi-model session | — | — | — | — | — | ${_label(claude['unallocated_multi_model_cost_usd'])} |",
            f"| **Total** | **{_int(claude['session_count'])} sessions** | **{_int(claude['totals']['input_tokens'])}** | **{_int(claude['totals']['output_tokens'])}** | **{_int(claude['totals']['cache_read_tokens'])}** | **{_int(claude['totals']['cache_write_tokens'])}** | **${Decimal(claude['reported_cost_usd']):.2f}** |",
            "",
            "Session appearances are not additive because a session may use more than one model. Cache reads and cache writes are reported separately and are not treated as normal input tokens.",
            "",
            "### OpenRouter model summary",
            "",
            "| Model | Provider | Requests | Prompt tokens | Completion tokens | Total reported cost | Share of cost |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in _model_rows(openrouter):
        share = row["cost"] / openrouter["cost"] * Decimal(100)
        lines.append(
            "| {} | {} | {} | {} | {} | ${} | {:.2f}% |".format(
                _model(row["model"]),
                _providers(row["provider"]),
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
            "> Claude Code includes four sessions that reported $0.00. One $15.65 multi-model session is retained as unallocated rather than assigning its cost to a model without evidence.",
            "",
            "Regenerate with a private input kept outside the repository:",
            "",
            "```bash",
            "python scripts/generate_usage_dashboard.py \\",
            "  --openrouter-input /absolute/private/path/openrouter_activity.csv \\",
            "  --claude-input data/claude-code-usage-aggregate.json \\",
            "  --output-dir docs/assets \\",
            "  --update-readme README.md",
            "```",
        ]
    )
    return "\n".join(lines) + "\n"


def update_readme(path: str | Path, content: str) -> None:
    try:
        readme = Path(path)
        original = readme.read_text(encoding="utf-8")
        if original.count(START) != 1 or original.count(END) != 1:
            raise DashboardError("README usage markers are missing or ambiguous")
        before, remainder = original.split(START, 1)
        _, after = remainder.split(END, 1)
        readme.write_text(before + START + "\n" + content + END + after, encoding="utf-8")
    except OSError:
        raise DashboardError("unable to update README") from None
