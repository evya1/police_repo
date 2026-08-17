"""Refusal codes and diagnostics.

Every refusal names *which* thing is wrong, because the difference decides
whose side the fix is on and how long it takes to find. A stranger MAY be
refused with a diagnosis; a refusal MUST travel as a ``receive_control``
message, because no tool return value can carry one (FR-8, FR-13).

SPAR-N00 through SPAR-N10 cover the negotiation surface. SPAR-N11 and
beyond are reserved for turn and audit refusals (ST-07/ST-08).
"""

from __future__ import annotations

#: Stable refusal codes for the negotiation surface.
REFUSAL_CODES: frozenset[str] = frozenset({
    "SPAR-N00",  # greeting is not a dict
    "SPAR-N01",  # terms absent
    "SPAR-N02",  # terms incomplete (missing keys)
    "SPAR-N03",  # terms value mismatch (constitution disagreement)
    "SPAR-N04",  # signature does not verify
    "SPAR-N05",  # locked-model mismatch (both declared and disagree)
    "SPAR-N06",  # sub-game mismatch
    "SPAR-N07",  # role collision (both same side)
    "SPAR-N08",  # no group_id in greeting
    "SPAR-N09",  # arrived (diagnostic only, not a refusal)
    "SPAR-N10",  # game_uid mismatch
    "SPAR-N11",  # turn validation failed
    "SPAR-N12",  # audit validation failed
    "SPAR-N13",  # position leak detected (FR-26/27)
})

#: Human-readable diagnostics for every negotiation refusal code.
_DIAGNOSTICS: dict[str, str] = {
    "SPAR-N00": "greeting is not a dict/object",
    "SPAR-N01": "opponent greeting carries no ``terms`` at all — a wire-shape fault",
    "SPAR-N02": "opponent terms are incomplete; missing one or more of the 14 required keys",
    "SPAR-N03": "opponent terms do not value-equal ours — a constitution disagreement",
    "SPAR-N04": "the terms signature does not verify — check canonicalization (ensure_ascii, separators)",
    "SPAR-N05": "locked-model mismatch: both peers declared and the hashes differ",
    "SPAR-N06": "sub-game mismatch: the two peers are playing different sub-game numbers",
    "SPAR-N07": "role collision: both peers declared the same role — the two sides must be complementary",
    "SPAR-N08": "greeting names no group_id, so no game_id can be derived",
    "SPAR-N09": "diagnostic only: opponent answered within the handshake budget",
    "SPAR-N10": "game_uid mismatch: declared uid differs from the uid derived from flat terms",
    "SPAR-N11": "turn message validation failed; the detail lists every bad field",
    "SPAR-N12": "audit payload validation failed; the detail lists every bad field",
    "SPAR-N13": "position leak: a non-position wire field carries numeric coordinates (FR-26/27)",
}


class Refused(Exception):  # noqa: N818
    """A refusal with a stable code so an operator can grep for it."""

    def __init__(self, code: str, message: str) -> None:
        if code not in REFUSAL_CODES:
            raise ValueError(f"unknown refusal code {code!r}")
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


def refuse(code: str, detail: str = "") -> dict:
    """Build a control-message refusal to send via ``receive_control``.

    A refusal cannot be a tool return value (FR-8), so it must travel as a
    control message. The ``kind`` field is always ``"refusal"``.
    """
    return {
        "kind": "refusal",
        "code": code,
        "detail": detail,
    }


def is_refusal(code: str) -> bool:
    """Return True when ``code`` is a known negotiation refusal code."""
    return code in REFUSAL_CODES


def diagnostic(code: str) -> str:
    """Return the human-readable diagnostic for a refusal code."""
    return _DIAGNOSTICS.get(code, f"unknown refusal code: {code}")
