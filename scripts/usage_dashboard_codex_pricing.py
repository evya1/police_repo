from __future__ import annotations

from decimal import Decimal

TOKEN_KEYS = (
    "input_tokens",
    "output_tokens",
    "reasoning_output_tokens",
    "cache_read_tokens",
    "cache_write_tokens",
)
RATE_KEYS = (
    "input_per_million_usd",
    "cached_input_per_million_usd",
    "cache_write_per_million_usd",
    "output_per_million_usd",
)
MODEL_PRICING = {
    "gpt-5.6-sol": (
        "GPT-5.6 Sol",
        dict(zip(RATE_KEYS, ("4.00", "0.40", "5.00", "20.00"), strict=True)),
    ),
    "gpt-5.6-luna": (
        "GPT-5.6 Luna",
        dict(zip(RATE_KEYS, ("0.20", "0.02", "0.25", "1.20"), strict=True)),
    ),
    "gpt-5.4-mini": (
        "GPT-5.4 Mini",
        dict(zip(RATE_KEYS, ("0.75", "0.075", None, "4.50"), strict=True)),
    ),
}


def model_details(slug: str) -> tuple[str, dict[str, str | None]]:
    for details in MODEL_PRICING.values():
        if slug == details[0]:
            return details
    return MODEL_PRICING.get(slug, (slug, dict.fromkeys(RATE_KEYS)))


def token_cost(tokens: dict[str, int], rates: dict[str, str | None]) -> Decimal | None:
    chargeable = (
        ("input_tokens", "input_per_million_usd"),
        ("cache_read_tokens", "cached_input_per_million_usd"),
        ("cache_write_tokens", "cache_write_per_million_usd"),
        ("output_tokens", "output_per_million_usd"),
    )
    if any(tokens[token] and rates[rate] is None for token, rate in chargeable):
        return None
    return sum(
        (Decimal(tokens[token]) * Decimal(rates[rate] or "0") for token, rate in chargeable),
        Decimal(0),
    ) / Decimal(1_000_000)


def sanitized_aggregate(
    models: dict[str, dict[str, int]], sessions: int, first: str, last: str,
    duration_ms: int = 0, duration_sessions: int = 0,
) -> dict[str, object]:
    rows = []
    pricing = {}
    total_cost = Decimal(0)
    unpriced = 0
    for slug in sorted(models):
        label, rates = model_details(slug)
        values = models[slug]
        cost = token_cost(values, rates)
        pricing[label] = rates
        if cost is None:
            unpriced += 1
        else:
            total_cost += cost
        rows.append({"model": label, **values, "attributed_cost_usd": None if cost is None else str(cost)})
    totals = {key: sum(row[key] for row in rows) for key in TOKEN_KEYS}
    return {
        "source": "Codex", "session_count": sessions, "first_day": first, "last_day": last,
        "cost_method": "estimated_api_list_price", "pricing": pricing, "models": rows,
        "totals": totals, "estimated_cost_usd": str(total_cost),
        "unpriced_model_count": unpriced, "recorded_duration_ms": duration_ms,
        "duration_session_count": duration_sessions,
    }
