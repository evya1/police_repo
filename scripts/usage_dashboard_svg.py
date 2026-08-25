from __future__ import annotations

from decimal import Decimal

import usage_dashboard_svg_primitives as ui
from usage_dashboard_data import combined_totals


def render_svg(openrouter: dict[str, object], claude: dict[str, object], theme: str) -> str:
    palette, css = ui.theme(theme)
    combined = combined_totals(openrouter, claude)
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {ui.WIDTH} {ui.HEIGHT}" '
        f'role="img" aria-label="Aggregated AI usage dashboard">',
        f"<style>{css}</style>",
        ui.rect(0, 0, ui.WIDTH, ui.HEIGHT, "", palette["bg"], 0),
        ui.text(36, 39, "AI usage", "heading"),
        ui.text(36, 61, "Accounted cost and aggregate token activity", "subheading"),
    ]
    cards = [
        ("Combined spend", ui.money(combined["cost"]), "#6D5BD0"),
        ("OpenRouter spend", ui.money(openrouter["cost"]), "#6D5BD0"),
        ("Claude Code spend", ui.money(Decimal(claude["accounted_cost_usd"])), "#D97706"),
        ("OpenRouter requests", f"{openrouter['requests']:,}", "#1597A8"),
    ]
    for index, card in enumerate(cards):
        out.extend(ui.card(36 + index * 284, 82, 264, *card))
    second = [
        ("Claude Code sessions", f"{claude['session_count']:,}", "#D97706"),
        ("Non-cache input / prompt", f"{combined['input']:,}", "#26865E"),
        ("Non-cache output / completion", f"{combined['output']:,}", "#C24170"),
    ]
    for index, card in enumerate(second):
        out.extend(ui.card(36 + index * 379, 174, 359, *card))
    out.extend(
        [
            ui.rect(36, 266, 758, 458, "card"),
            ui.rect(814, 266, 350, 458, "card"),
            ui.text(60, 298, "OpenRouter daily reported cost", "section"),
            ui.text(838, 298, "Accounted cost by source", "section"),
        ]
    )
    top = ui.top_models(openrouter)
    legend = [(name, ui.MODEL_COLORS[i]) for i, name in enumerate(top)] + [
        ("Other", ui.OTHER_COLOR)
    ]
    for index, (name, color) in enumerate(legend):
        x = 60 + index * 119
        out.append(ui.rect(x, 313, 10, 10, "", color, 2))
        out.append(ui.text(x + 15, 322, ui.short(name), "small"))
    days = sorted(openrouter["daily"])
    totals = {day: sum(openrouter["daily"][day].values(), Decimal(0)) for day in days}
    maximum = max(totals.values(), default=Decimal(1))
    plot_y, plot_height, baseline = 354.0, 284.0, 638.0
    for index in range(5):
        y = plot_y + index * plot_height / 4
        out.append(f'<line x1="62" y1="{y:.1f}" x2="770" y2="{y:.1f}" class="grid"/>')
        value = maximum * Decimal(4 - index) / Decimal(4)
        if index < 4:
            out.append(ui.text(67, y - 5, ui.money(value), "axis"))
    bar_width = 78.0
    gap = (680 - bar_width * len(days)) / max(len(days) - 1, 1)
    for day_index, day in enumerate(days):
        x = 76 + day_index * (bar_width + gap)
        cursor = baseline
        known = sum((openrouter["daily"][day].get(name, Decimal(0)) for name in top), Decimal(0))
        segments = [
            (openrouter["daily"][day].get(name, Decimal(0)), ui.MODEL_COLORS[i])
            for i, name in enumerate(top)
        ]
        segments.append((totals[day] - known, ui.OTHER_COLOR))
        for amount, color in segments:
            height = float(amount / maximum) * plot_height if maximum else 0
            cursor -= height
            if height > 0:
                out.append(ui.rect(x, cursor, bar_width, height, "", color, 2))
        out.append(ui.text(x + bar_width / 2, baseline + 20, ui.date_label(day), "axis", "middle"))
        out.append(ui.text(x + bar_width / 2, cursor - 7, ui.money(totals[day]), "small", "middle"))
    source_costs = [
        ("Claude Code", Decimal(claude["accounted_cost_usd"]), "#D97706"),
        ("OpenRouter", openrouter["cost"], "#6D5BD0"),
    ]
    source_max = max(value for _, value, _ in source_costs)
    for index, (name, value, color) in enumerate(source_costs):
        y = 338 + index * 84
        out.extend(
            [
                ui.text(840, y, name, "label"),
                ui.text(
                    1138,
                    y,
                    ui.money(value, "0.000001") if name == "OpenRouter" else ui.money(value),
                    "small",
                    "end",
                ),
                ui.rect(840, y + 12, 298, 18, "", palette["line"], 5),
                ui.rect(840, y + 12, float(value / source_max) * 298, 18, "", color, 5),
            ]
        )
    out.extend(
        [
            ui.text(840, 508, "Claude Code aggregate", "section"),
            ui.text(840, 538, f"{claude['session_count']} deduplicated sessions", "subheading"),
            ui.text(
                840,
                564,
                f"{claude['zero_reported_cost_sessions']} sessions reported $0.00",
                "subheading",
            ),
            ui.text(840, 590, "$15.65 retained as unallocated", "subheading"),
            ui.text(840, 687, "Aggregate data only • no request or session records", "small"),
            "</svg>",
        ]
    )
    return "\n".join(out) + "\n"
