"""Turn and audit validation for the reference-v3 wire shape.

Validation runs before any state change: a receiver must reject the whole turn if a single
field is wrong, because a partially-applied bad turn is unrecoverable (FR-25). Unknown keys
are TOLERATED — the extension seam (FR-20). Every problem is named so the sender fixes its
encoder in one round trip instead of six.
"""

from __future__ import annotations

TURN_OPTIONAL_KEYS = frozenset({
    "barrier_placed",
    "capture_claim",
    "claim_response",
    "win_claim",
})

# Position-carrying fields: the only wire shapes allowed to carry numeric coordinates.
_POSITION_FIELDS = frozenset({"barrier_placed", "capture_claim"})


def validate_turn(data: dict) -> str:
    """Validate an inbound TurnMessage before any state change.

    Returns ``"accept"`` or ``"<field>: <reason>; ..."``. Every problem is enumerated so the
    sender fixes its encoder in one round trip (FR-25).

    Unknown keys are tolerated and silently dropped (FR-20 extension seam).
    """
    problems: list[str] = []

    step = data.get("step")
    if not isinstance(step, int) or isinstance(step, bool) or step < 0:
        problems.append("step: required non-negative int")

    for name in ("sender", "timestamp"):
        value = data.get(name)
        if not isinstance(value, str) or not value:
            problems.append(f"{name}: required non-empty str")

    hint = data.get("hint")
    if not isinstance(hint, str):
        problems.append("hint: required str (may be empty)")

    grid = data.get("smell_grid")
    if not isinstance(grid, dict) or not all(
        isinstance(k, str) and isinstance(v, (int, float)) and not isinstance(v, bool)
        for k, v in grid.items()
    ):
        problems.append("smell_grid: required dict of 'r,c' -> number")

    commit = data.get("commit")
    if not (isinstance(commit, str) and len(commit) == 64
            and all(c in "0123456789abcdef" for c in commit)):
        problems.append("commit: required 64-char lowercase hex")

    for name in ("barrier_placed", "capture_claim"):
        cell = data.get(name)
        if cell is not None and not (
            isinstance(cell, (list, tuple)) and len(cell) == 2
            and all(isinstance(i, int) and not isinstance(i, bool) for i in cell)
        ):
            problems.append(f"{name}: optional [row, col] of ints, or null")

    return "accept" if not problems else "; ".join(problems)


def validate_audit(data: dict) -> str:
    """Validate an inbound AuditPayload before any state change.

    Returns ``"accept"`` or ``"<field>: <reason>; ..."``.
    """
    problems: list[str] = []

    sender = data.get("sender")
    if not isinstance(sender, str) or not sender:
        problems.append("sender: required non-empty str")

    records = data.get("records")
    if not isinstance(records, list):
        problems.append("records: required list")

    result_claim = data.get("result_claim")
    if not isinstance(result_claim, str) or not result_claim:
        problems.append("result_claim: required non-empty str")

    return "accept" if not problems else "; ".join(problems)


def assert_no_position_leak(turn: dict) -> None:
    """Raise if a numeric position leaks into a non-position field (FR-26, FR-27).

    Only ``barrier_placed`` and ``capture_claim`` may carry numeric coordinates. The ``hint``
    field is text-only by rule (NET-004). This check is a structural guard: a strategy that
    encodes a coordinate into the hint string is a silent position leak.

    Known numeric-but-not-position fields (``step``, ``smell_grid`` values) are excluded.
    """
    _known_numeric = frozenset({"step"})
    for name, value in turn.items():
        if name in TURN_OPTIONAL_KEYS:
            continue
        if name in _POSITION_FIELDS:
            continue
        if name in _known_numeric:
            continue
        # Any bare numeric value in a non-position, non-optional field is a leak.
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            raise ValueError(
                f"position leak: {name} carries a numeric value "
                f"({value}); only {', '.join(sorted(_POSITION_FIELDS))} may carry coordinates"
            )
        # A 2-int list in a non-position field is a coordinate leak (smell_grid is a dict).
        if (isinstance(value, (list, tuple)) and len(value) == 2
                and name not in _POSITION_FIELDS
                and all(isinstance(i, int) and not isinstance(i, bool) for i in value)):
            raise ValueError(
                f"position leak: {name} carries a 2-int coordinate; "
                f"only {', '.join(sorted(_POSITION_FIELDS))} may carry coordinates"
            )
