"""Turn, control, and audit message shapes with validation.

STUB — to be replaced by the real implementation in ST-07 (T009).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TurnMessage:
    """A turn message exchanged between peers."""

    step: int = 0
    sender: str = ""
    hint: str = ""
    smell_grid: dict[str, float] = field(default_factory=dict)
    commit: str = ""
    timestamp: str = ""
    # Extra keys tolerated and ignored (FR-20 extension seam).
    _extra: dict[str, Any] = field(default_factory=dict, repr=False)


@dataclass
class ControlMessage:
    """A control signal exchanged between peers."""

    kind: str = ""
    code: str = ""
    detail: str = ""


@dataclass
class AuditPayload:
    """An end-of-game audit reveal."""

    records: list[dict] = field(default_factory=list)
    nonces: list[str] = field(default_factory=list)
    result_claim: str = ""


def to_wire(msg: TurnMessage) -> dict:
    """Serialize a TurnMessage to a wire dict.

    STUB: placeholder.
    """
    return {
        "step": msg.step,
        "sender": msg.sender,
        "hint": msg.hint,
        "smell_grid": msg.smell_grid,
        "commit": msg.commit,
        "timestamp": msg.timestamp,
        **msg._extra,
    }


def from_wire(data: dict) -> TurnMessage:
    """Parse a TurnMessage from a wire dict.

    Unknown keys are dropped (FR-20 extension seam).
    """
    known_keys = {"step", "sender", "hint", "smell_grid", "commit", "timestamp"}
    extra = {k: v for k, v in data.items() if k not in known_keys}
    return TurnMessage(
        step=data.get("step", 0),
        sender=data.get("sender", ""),
        hint=data.get("hint", ""),
        smell_grid=data.get("smell_grid", {}),
        commit=data.get("commit", ""),
        timestamp=data.get("timestamp", ""),
        _extra=extra,
    )


def validate_turn(data: dict) -> tuple[bool, str]:
    """Validate a turn message dict. Return (valid, reason).

    STUB: minimal validation.
    All decisions are made before any state change (FR-25).
    """
    required_keys = {"step", "sender", "hint", "smell_grid", "commit", "timestamp"}
    missing = required_keys - set(data.keys())
    if missing:
        return False, f"missing required keys: {', '.join(sorted(missing))}"
    if not data.get("smell_grid"):
        return False, "smell_grid is empty"
    if not isinstance(data.get("timestamp"), str) or not data["timestamp"]:
        return False, "timestamp is empty or not a string"
    return True, "ok"


def validate_audit(data: dict) -> tuple[bool, str]:
    """Validate an audit payload dict. Return (valid, reason).

    STUB: minimal validation.
    """
    if "records" not in data:
        return False, "missing 'records' key"
    if "nonces" not in data:
        return False, "missing 'nonces' key"
    return True, "ok"


def assert_no_position_leak(turn: dict) -> bool:
    """Return True when the turn carries no numeric position leak.

    FR-26/27: only `barrier_placed` and `capture_claim` may carry numeric
    positions; `hint` must be text-only.
    """
    # STUB: placeholder
    return True
