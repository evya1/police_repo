"""Live audit physics prefers an explicit sealed `position` (T054).

`check_physics` derives its position trail from the sealed record. Before T054 it read
ONLY the `state` string, through a regex pinned to *our own* `self=[r, c]` spelling. A
conforming kit peer seals an explicit `position` and may spell `state` differently -- and
an unparseable spelling made every physics check silently skip, so an illegal jump passed
unnoticed. That is the worst failure mode for an audit: not a wrong answer, but no answer
presented as a clean one.

Preferring a strictly-parsed explicit position gives real coverage; `state` stays the
fallback so existing internal bundles keep exactly the coverage they had. A malformed or
foreign position degrades to the fallback -- never to a loose re-read into the wrong cell,
and never to a manufactured tamper claim.
"""

from __future__ import annotations

from common.transport.audit_physics import check_physics

_TERMS = {"board_size": 7, "max_steps": 35, "barriers_max": 14}


# --- explicit kit `position` is preferred over legacy `state` parsing (T054) -----------


def test_explicit_position_is_used_when_state_spelling_is_foreign() -> None:
    """A kit peer seals an explicit `position`, but may spell `state` differently than our
    own `self=[r, c]` convention. Before T054 physics read ONLY `state`, so an unparseable
    foreign spelling made every physics check silently skip -- an illegal two-cell jump
    passed unnoticed. Preferring the explicit, strictly-parsed position gives real coverage
    instead of accidental silence.
    """
    records = [
        {"step": 1, "position": [0, 0], "state": "grid=7x7|me:(0,0)|walls:none"},
        {"step": 2, "position": [3, 3], "state": "grid=7x7|me:(3,3)|walls:none"},
    ]
    problems = check_physics(records, _TERMS)
    assert any("orthogonal step" in msg for _, msg in problems), (
        f"illegal jump [0,0] -> [3,3] went undetected; problems={problems}"
    )


def test_legacy_state_only_records_still_verify() -> None:
    """Internal/older records carry no explicit position; `state` parsing stays the
    fallback so existing bundles keep exactly the coverage they had."""
    records = [
        {"step": 1, "state": "grid=7x7;self=[0, 0];barriers=[]"},
        {"step": 2, "state": "grid=7x7;self=[3, 3];barriers=[]"},
    ]
    problems = check_physics(records, _TERMS)
    assert any("orthogonal step" in msg for _, msg in problems)


def test_malformed_position_degrades_to_state_not_to_an_accusation() -> None:
    """A malformed/foreign position must never be loosely re-read into the wrong cell.
    Strict parse fails -> fall back to `state` -> if that is also unreadable, skip the
    physics layer rather than manufacture a tamper claim."""
    records = [
        {"step": 1, "position": "0,0", "state": "grid=7x7;self=[0, 0];barriers=[]"},
        {"step": 2, "position": [True, False], "state": "grid=7x7;self=[0, 1];barriers=[]"},
    ]
    problems = check_physics(records, _TERMS)
    assert problems == [], f"a legal one-step walk was accused: {problems}"
