"""Model lock — pinned parameter documents, canonical hashing, and refusal decision.

The two scent_model documents and the refusal truth table are the registered families needed
for T005; their parameters are those specified in M-01 §B and pinned in
``vectors/locked_model.json``.

STRAT-005: before a series, both parties exchange the complete emission-and-decay model with a
numeric example, confirm identical interpretation, and cryptographically lock the agreement.
"""

from __future__ import annotations

import hashlib
import json
from typing import Literal

# Build the exact doc objects from the registered documents in vectors/locked_model.json.
# The subtractive_chebyshev_v1 doc (L22–107) and the multiplicative_book_v1 doc (L114–180).
PINNED_DOCS: dict[str, dict] = {
    "subtractive_chebyshev_v1": {
        "family": "scent_model",
        "name": "subtractive_chebyshev_v1",
        "params": {
            "field_size": 5,
            "emit_intensity": 0.9,
            "min_center_intensity": 0.5,
            "distance": "chebyshev",
            "falloff": "linear",
            "falloff_step": "emit_intensity / (field_size // 2 + 1)",
            "decay": "subtractive",
            "decay_per_step": 0.1,
            "update": "tau' = round(max(0, tau - decay_per_step), 3)",
            "rounding_decimals": 3,
            "clamp": [0.0, None],
            "cadence": "per_full_turn",
            "order": "deposit_then_decay",
            "receiver_side_decay": True,
            "initial_field": "empty",
            "transmitted": True,
        },
        "example": {
            "note": "emit at the centre of a 7x7 board, then one decay",
            "emit_center": [3, 3],
            "emit_field": {
                "1,1": 0.3, "1,2": 0.3, "1,3": 0.3, "1,4": 0.3, "1,5": 0.3,
                "2,1": 0.3, "2,2": 0.6, "2,3": 0.6, "2,4": 0.6, "2,5": 0.3,
                "3,1": 0.3, "3,2": 0.6, "3,3": 0.9, "3,4": 0.6, "3,5": 0.3,
                "4,1": 0.3, "4,2": 0.6, "4,3": 0.6, "4,4": 0.6, "4,5": 0.3,
                "5,1": 0.3, "5,2": 0.3, "5,3": 0.3, "5,4": 0.3, "5,5": 0.3,
            },
            "after_one_decay": {
                "1,1": 0.2, "1,2": 0.2, "1,3": 0.2, "1,4": 0.2, "1,5": 0.2,
                "2,1": 0.2, "2,2": 0.5, "2,3": 0.5, "2,4": 0.5, "2,5": 0.2,
                "3,1": 0.2, "3,2": 0.5, "3,3": 0.8, "3,4": 0.5, "3,5": 0.2,
                "4,1": 0.2, "4,2": 0.5, "4,3": 0.5, "4,4": 0.5, "4,5": 0.2,
                "5,1": 0.2, "5,2": 0.2, "5,3": 0.2, "5,4": 0.2, "5,5": 0.2,
            },
        },
    },
    "multiplicative_book_v1": {
        "family": "scent_model",
        "name": "multiplicative_book_v1",
        "params": {
            "field_size": 5,
            "center_intensity": 0.9,
            "decay_rho": 0.1,
            "kernel": [
                [0.04, 0.14, 0.2, 0.14, 0.04],
                [0.14, 0.42, 0.62, 0.42, 0.14],
                [0.2, 0.62, 0.9, 0.62, 0.2],
                [0.14, 0.42, 0.62, 0.42, 0.14],
                [0.04, 0.14, 0.2, 0.14, 0.04],
            ],
            "kernel_source": "book v3.0.0 figure 4 — printed values, verbatim lookup",
            "decay": "multiplicative",
            "update": "tau' = clamp((1 - rho) * tau + kernel_delta, 0, center_intensity)",
            "evaluation_order": "(1 - rho) * tau + delta, then clamp",
            "rounding_decimals": None,
            "clamp": [0.0, 0.9],
            "cadence": "per_full_turn",
            "order": "decay_then_deposit",
            "receiver_side_decay": False,
            "initial_field": "empty",
            "transmitted": False,
        },
        "example": {
            "note": "the clamp case: a saturated cell decays, then takes an adjacent deposit",
            "tau": 0.9,
            "delta": 0.62,
            "raw": 1.4300000000000002,
            "clamped": 0.9,
        },
    },
}


def canonical_json(obj: object) -> str:
    """SPEC §2: compact canonical JSON serialization for hashable comparison."""
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def model_lock_hash(model: str) -> str:
    """SHA-256 of the canonical JSON over the registered doc for the named model."""
    doc = PINNED_DOCS[model]
    return hashlib.sha256(canonical_json(doc).encode("utf-8")).hexdigest()


# Published hash values from vectors/locked_model.json — asserted in tests.
_SUBTRACTIVE_HASH = "81ebee59640e80eae8ca9ee5f86abd26e7edf5cdbb27d15925cb6ee45ca6ddf4"
_BOOK_HASH = "934c220d5bf62acaa3297c6c9d723ea954c220260b02292ca17f6d5daef9f4d9"


def refusal_decision(
    ours: str | None, theirs: str | None
) -> Literal["play", "refuse"]:
    """The 5-row truth table from locked_model.json refusal_rule.

    * Both declare and same hash → play
    * Both declare and different hashes → refuse
    * Exactly one declares → play
    * Neither declares → play
    """
    if ours is not None and theirs is not None:
        return "refuse" if ours != theirs else "play"
    return "play"
