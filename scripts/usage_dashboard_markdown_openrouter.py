from __future__ import annotations

from decimal import Decimal
from html import escape

MODEL_LINKS = {
    "google/gemini-3.7-flash-20260813": (
        "Google: Gemini 3.7 Flash",
        "google/gemini-3.7-flash",
    ),
    "z-ai/glm-5.2-20260616": ("Z.ai: GLM 5.2", "z-ai/glm-5.2"),
    "deepseek/deepseek-v4-pro-20260813": (
        "DeepSeek: DeepSeek V4 Pro 0813",
        "deepseek/deepseek-v4-pro-0813",
    ),
    "google/gemini-3.1-pro-preview-20260219": (
        "Google: Gemini 3.1 Pro Preview",
        "google/gemini-3.1-pro-preview",
    ),
    "deepseek/deepseek-v4-pro-20260423": (
        "DeepSeek: DeepSeek V4 Pro 0423",
        "deepseek/deepseek-v4-pro",
    ),
    "google/gemini-2.5-pro": ("Google: Gemini 2.5 Pro", "google/gemini-2.5-pro"),
    "deepseek/deepseek-v4-flash-20260731": (
        "DeepSeek: DeepSeek V4 Flash 0731",
        "deepseek/deepseek-v4-flash-0731",
    ),
    "moonshotai/kimi-k2.6-20260420": (
        "MoonshotAI: Kimi K2.6",
        "moonshotai/kimi-k2.6",
    ),
}
PROVIDERS = frozenset(
    {
        "Alibaba",
        "Baidu",
        "Crusoe",
        "Decart",
        "DigitalOcean",
        "Fireworks",
        "Friendli",
        "GMICloud",
        "Morph",
        "Novita",
        "Parasail",
        "Relace",
        "SiliconFlow",
        "StreamLake",
        "Together",
    }
)
PROVIDER_DISPLAY = {
    "Alibaba": "Alibaba Cloud Int.",
    "Baidu": "Baidu Qianfan",
    "Novita": "NovitaAI",
}
PROVIDER_EXTENSIONS = {"SiliconFlow": "svg", "Morph": "jpg"}


def _label(value: object) -> str:
    return escape(str(value), quote=True).replace("|", "&#124;")


def model(value: object) -> str:
    link = MODEL_LINKS.get(str(value))
    return _label(value) if link is None else f"[{link[0]}](https://openrouter.ai/{link[1]})"


def _provider(value: object) -> str:
    name = str(value)
    if name not in PROVIDERS:
        return _label(value)
    slug = name.lower()
    extension = PROVIDER_EXTENSIONS.get(name, "png")
    display = PROVIDER_DISPLAY.get(name, name)
    return f'<a href="https://openrouter.ai/provider/{slug}"><img src="docs/assets/providers/{slug}.{extension}" width="16" alt=""> {display}</a>'


def providers(value: object) -> str:
    return (
        ", ".join(_provider(item) for item in value) if isinstance(value, list) else _label(value)
    )


def model_rows(openrouter: dict[str, object], limit: int = 8) -> list[dict[str, object]]:
    ranked = sorted(openrouter["models"].items(), key=lambda item: (-item[1]["cost"], item[0]))
    rows = [
        {"model": name, "provider": sorted(item["providers"]), **item}
        for name, item in ranked[:limit]
    ]
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
