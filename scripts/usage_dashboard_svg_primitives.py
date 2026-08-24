from __future__ import annotations

from decimal import Decimal
from html import escape

WIDTH = 1200
HEIGHT = 760
MODEL_COLORS = ("#6D5BD0", "#1597A8", "#D97706", "#26865E", "#C24170")
OTHER_COLOR = "#7B8496"


def theme(theme_name: str) -> tuple[dict[str, str], str]:
    if theme_name not in {"light", "dark"}:
        raise ValueError("unsupported theme")
    dark = theme_name == "dark"
    palette = {
        "bg": "#10131A" if dark else "#F5F7FB",
        "card": "#181D27" if dark else "#FFFFFF",
        "text": "#F2F4F8" if dark else "#19202B",
        "muted": "#AAB3C2" if dark else "#5C6678",
        "line": "#333B4A" if dark else "#E2E7EF",
    }
    css = (
        "text{{font-family:Arial,sans-serif}}.heading{{font-size:24px;font-weight:700;fill:{}}}"
        ".subheading{{font-size:14px;fill:{}}}.label{{font-size:12px;fill:{}}}"
        ".value{{font-size:23px;font-weight:700;fill:{}}}.section{{font-size:16px;"
        "font-weight:700;fill:{}}}.small{{font-size:11px;fill:{}}}.axis{{font-size:11px;"
        "fill:{}}}.card{{fill:{};stroke:{};stroke-width:1}}.grid{{stroke:{};stroke-width:1}}"
    ).format(
        palette["text"],
        palette["muted"],
        palette["muted"],
        palette["text"],
        palette["text"],
        palette["muted"],
        palette["muted"],
        palette["card"],
        palette["line"],
        palette["line"],
    )
    return palette, css


def text(x: float, y: float, value: object, css: str, anchor: str = "start") -> str:
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" class="{css}" text-anchor="{anchor}">'
        f"{escape(str(value))}</text>"
    )


def rect(
    x: float,
    y: float,
    width: float,
    height: float,
    css: str,
    fill: str | None = None,
    radius: int = 12,
) -> str:
    color = f' fill="{fill}"' if fill else ""
    return (
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{width:.1f}" height="{height:.1f}" '
        f'rx="{radius}" class="{css}"{color}/>'
    )


def short(label: str, limit: int = 17) -> str:
    compact = label.rsplit("/", 1)[-1]
    return compact if len(compact) <= limit else compact[: limit - 1] + "…"


def top_models(openrouter: dict[str, object], limit: int = 5) -> list[str]:
    ranked = sorted(openrouter["models"].items(), key=lambda item: (-item[1]["cost"], item[0]))
    return [name for name, _ in ranked[:limit]]


def money(value: Decimal, places: str = "0.01") -> str:
    return f"${value.quantize(Decimal(places)):,.{len(places) - 2}f}"


def card(x: float, y: float, width: float, label: str, value: str, accent: str) -> list[str]:
    return [
        rect(x, y, width, 78, "card"),
        rect(x, y, 5, 78, "", accent, 3),
        text(x + 20, y + 28, label, "label"),
        text(x + 20, y + 59, value, "value"),
    ]


def date_label(day: str) -> str:
    months = {"08": "Aug"}
    return f"{months.get(day[5:7], day[5:7])} {int(day[8:10])}"
