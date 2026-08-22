"""Turn and audit validation for the reference-v3 wire shape.

Validation runs before any state change: a receiver must reject the whole turn if a single
field is wrong, because a partially-applied bad turn is unrecoverable (FR-25). Unknown keys
are TOLERATED — the extension seam (FR-20) — unless they smuggle a bare coordinate, which is
a position leak (FR-26/27) and is refused here rather than raised at the caller. Every
problem is named so the sender fixes its encoder in one round trip instead of six.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

TURN_OPTIONAL_KEYS = frozenset({
    "barrier_placed",
    "capture_claim",
    "claim_response",
    "win_claim",
})

# Position-carrying fields: the only wire shapes allowed to carry numeric coordinates.
_POSITION_FIELDS = frozenset({"barrier_placed", "capture_claim"})

#: The only sender values that appear on the wire (``Role`` values, kept literal so this
#: module stays a leaf with no domain import).
_SENDERS = frozenset({"police", "thief"})

#: The only outcomes a peer may declare for itself in ``win_claim``.
_WIN_CLAIM_TYPES = frozenset({"capture", "survival"})


def _is_plain_int(value: object) -> bool:
    """True for a real int; ``bool`` is an int subclass and is never a coordinate."""
    return isinstance(value, int) and not isinstance(value, bool)


def _cell_problem(value: object, board_size: int) -> str | None:
    """None when ``value`` is an in-bounds ``[row, col]``; otherwise the reason it is not."""
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return "required [row, col] of ints"
    if len(value) != 2 or not all(_is_plain_int(item) for item in value):
        return "required [row, col] of ints"
    if not all(0 <= int(item) < board_size for item in value):
        return f"out of bounds for the negotiated {board_size}x{board_size} board"
    return None


def _optional_cell_problems(data: Mapping, board_size: int) -> list[str]:
    """Problems in the optional coordinate fields (absent/null is always fine)."""
    problems: list[str] = []
    for name in sorted(_POSITION_FIELDS):
        cell = data.get(name)
        if cell is None:
            continue
        reason = _cell_problem(cell, board_size)
        if reason is not None:
            problems.append(f"{name}: {reason}, or null")
    return problems


def _claim_response_problems(value: object, board_size: int) -> list[str]:
    """Problems in ``claim_response`` — the thief's honest answer, ``{claim, caught}``."""
    if not isinstance(value, Mapping):
        return ["claim_response: required mapping {claim: [row, col], caught: bool}, or null"]
    problems: list[str] = []
    reason = _cell_problem(value.get("claim"), board_size)
    if reason is not None:
        problems.append(f"claim_response.claim: {reason}")
    if not isinstance(value.get("caught"), bool):
        problems.append("claim_response.caught: required bool")
    return problems


def _win_claim_problems(value: object) -> list[str]:
    """Problems in ``win_claim`` — a mapping naming one supported outcome."""
    if not isinstance(value, Mapping):
        return ["win_claim: required mapping {type: capture|survival}, or null"]
    kind = value.get("type")
    if not isinstance(kind, str) or kind not in _WIN_CLAIM_TYPES:
        return ["win_claim.type: required one of capture, survival"]
    return []


def _required_field_problems(data: Mapping) -> list[str]:
    """Problems in the always-present turn fields."""
    problems: list[str] = []
    step = data.get("step")
    if not _is_plain_int(step) or step < 0:
        problems.append("step: required non-negative int")

    sender = data.get("sender")
    if not isinstance(sender, str) or sender not in _SENDERS:
        problems.append(f"sender: required one of {', '.join(sorted(_SENDERS))}")

    timestamp = data.get("timestamp")
    if not isinstance(timestamp, str) or not timestamp:
        problems.append("timestamp: required non-empty str")

    if not isinstance(data.get("hint"), str):
        problems.append("hint: required str (may be empty)")

    grid = data.get("smell_grid")
    if not isinstance(grid, Mapping) or not all(
        isinstance(k, str) and isinstance(v, (int, float)) and not isinstance(v, bool)
        for k, v in grid.items()
    ):
        problems.append("smell_grid: required dict of 'r,c' -> number")

    commit = data.get("commit")
    if not (isinstance(commit, str) and len(commit) == 64
            and all(c in "0123456789abcdef" for c in commit)):
        problems.append("commit: required 64-char lowercase hex")
    return problems


def validate_turn(data: object, *, board_size: int) -> str:
    """Validate an inbound TurnMessage before any state change.

    A pure function of the message plus the NEGOTIATED board size — bounds belong to the
    agreed constitution, never to a hard-coded 7. A bad ``board_size`` is a programmer error
    and raises; a bad *message* is always a verdict, so hostile input can never reach a
    caller as an ``AttributeError``. Unknown keys stay tolerated (FR-20) unless they carry a
    coordinate. Returns ``"accept"`` or ``"<field>: <reason>; ..."`` naming every problem.
    """
    if not _is_plain_int(board_size) or board_size <= 0:
        raise ValueError(f"board_size must be a positive int, got {board_size!r}")
    if not isinstance(data, Mapping):
        return f"message: required mapping, got {type(data).__name__}"

    problems = _required_field_problems(data)
    problems.extend(_optional_cell_problems(data, board_size))
    if data.get("claim_response") is not None:
        problems.extend(_claim_response_problems(data["claim_response"], board_size))
    if data.get("win_claim") is not None:
        problems.extend(_win_claim_problems(data["win_claim"]))
    try:
        assert_no_position_leak(data)
    except ValueError as exc:
        problems.append(str(exc))

    return "accept" if not problems else "; ".join(problems)


def validate_audit(data: object) -> str:
    """Validate an inbound AuditPayload before any state change.

    Returns ``"accept"`` or ``"<field>: <reason>; ..."``.
    """
    if not isinstance(data, Mapping):
        return f"message: required mapping, got {type(data).__name__}"
    problems: list[str] = []

    sender = data.get("sender")
    if not isinstance(sender, str) or not sender:
        problems.append("sender: required non-empty str")

    if not isinstance(data.get("records"), list):
        problems.append("records: required list")

    result_claim = data.get("result_claim")
    if not isinstance(result_claim, str) or not result_claim:
        problems.append("result_claim: required non-empty str")

    return "accept" if not problems else "; ".join(problems)


def assert_no_position_leak(turn: Mapping) -> None:
    """Raise if a numeric position leaks into a non-position field (FR-26, FR-27).

    Only ``barrier_placed`` and ``capture_claim`` may carry numeric coordinates; ``hint`` is
    text-only by rule (NET-004). Known numeric-but-not-position fields (``step``,
    ``smell_grid`` values) are excluded.
    """
    _known_numeric = frozenset({"step"})
    for name, value in turn.items():
        if name in TURN_OPTIONAL_KEYS or name in _known_numeric:
            continue
        # Any bare numeric value in a non-position, non-optional field is a leak.
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            raise ValueError(
                f"position leak: {name} carries a numeric value "
                f"({value}); only {', '.join(sorted(_POSITION_FIELDS))} may carry coordinates"
            )
        # A 2-int list in a non-position field is a coordinate leak (smell_grid is a dict).
        if (isinstance(value, (list, tuple)) and len(value) == 2
                and all(isinstance(i, int) and not isinstance(i, bool) for i in value)):
            raise ValueError(
                f"position leak: {name} carries a 2-int coordinate; "
                f"only {', '.join(sorted(_POSITION_FIELDS))} may carry coordinates"
            )
