"""Shape adapter between the kit's nested sealed-record shape and the repository's flat record shape.

Pure, deterministic conversion functions with round-trip identity under canonicalization.
The flat re-hash payload is exactly the kit payload — re-hashing ``from_kit_record(r)``
reproduces ``r["commit"]`` byte-for-byte.
"""

from __future__ import annotations

import re


def from_kit_record(record: dict) -> dict:
    """Convert a nested kit record to a flat repo record.

    ``{"payload": {...}, "nonce": str, "commit": str}`` → ``{..., "nonce": str,
    "commit": str}`` where ``...`` is the payload expanded inline.
    """
    payload = record.get("payload", {})
    return {**payload, "nonce": record["nonce"], "commit": record["commit"]}


def to_kit_record(flat: dict) -> dict:
    """Convert a flat repo record to a nested kit record.

    ``{..., "nonce": str, "commit": str}`` → ``{"payload": {...}, "nonce": str,
    "commit": str}`` where ``...`` is the flat record minus ``nonce`` and ``commit``.
    """
    payload = {k: v for k, v in flat.items() if k not in ("nonce", "commit")}
    return {"payload": payload, "nonce": flat["nonce"], "commit": flat["commit"]}


def flat_steps_to_kit_doc(steps: list[dict], opponent_steps: list[dict] | None) -> dict:
    """Convert record lists to the ``records`` / ``opponent_records`` fragment of a kit log doc."""
    kit_records = [to_kit_record(r) for r in steps]
    result: dict = {"records": kit_records}
    if opponent_steps is not None:
        result["opponent_records"] = [to_kit_record(r) for r in opponent_steps]
    return result


def is_foreign_record(payload: dict) -> bool:
    """Return True when the payload carries no parseable repo-state string.

    Foreign kit shape uses position lists instead of the repo's
    ``grid=…;self=[r, c];barriers=…`` string. A record whose payload lacks a
    parseable ``state`` is treated as foreign — the harness verifies it
    integrity-only and reports degraded coverage (D-03, FR-RP-10).
    """
    state = payload.get("state", "")
    if not state or not isinstance(state, str):
        return True
    return re.search(r"self=\[(-?\d+),\s*(-?\d+)\]", state) is None
