"""Scent model — two registered profiles behind one small common interface.

Exports:
* ``Trail`` — per-agent scent field wrapper.
* ``MODELS``, ``DEFAULT_MODEL`` — registered model names.
* ``make_trail`` — factory that defaults to ``DEFAULT_MODEL``.
* ``hottest`` — strongest cell in an observed field.
* ``Cell`` — re-export of the board cell type alias.
"""

from police_peer.scent.lock import (
    PINNED_DOCS,
    canonical_json,
    model_lock_hash,
    refusal_decision,
)
from police_peer.scent.model import (
    BOOK_MODEL,
    DEFAULT_MODEL,
    MODELS,
    REFERENCE_MODEL,
    Cell,
    Trail,
    hottest,
    make_trail,
)

__all__ = [
    "BOOK_MODEL",
    "Cell",
    "DEFAULT_MODEL",
    "MODELS",
    "PINNED_DOCS",
    "REFERENCE_MODEL",
    "Trail",
    "canonical_json",
    "hottest",
    "make_trail",
    "model_lock_hash",
    "refusal_decision",
]
