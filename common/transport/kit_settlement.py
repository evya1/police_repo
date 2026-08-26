"""Series settlement: rows in, derived aggregate and consensus digest out (CT-07, ADR-012).

EVERYTHING in the aggregate is DERIVED from the rows -- totals are the sum of row scores,
``sub_games_won`` and ``ties`` are counted off them, ``tokens_total_series`` is the per-row
sum. Nothing is declared beside a derived value, because two peers that agree on the rows then
agree on every aggregate by construction, and that is what makes one settlement digest
possible at all.

Two award rules, and they land in different places:

* The TIE score is ADDITIVE at series level (``series_add``). On a level series the App. F tie
  score is added to each side's total, and the addend is published as ``tie_score_each`` so it
  is visible to anyone diffing two reports rather than hidden inside a number. The book puts
  the award at series level on the accumulated score; the reference peer awards it per
  sub-game and sums. Both readings are live in the league and they are invisible until a
  series actually ties, so ours is stated here and in the README rather than assumed.
* The DIVERSITY reward is NOT additive. It rides ``diversity_reward_applied`` and never enters
  ``total_score`` -- the league table applies it. A +10 baked into a total is refused by the
  kit's own checker, with a diagnosis.

A zeroed sub-game (timeout, technical loss, tamper forfeit) is a sanction, not a tie: it is
credited to nobody, so it is counted as its own term rather than folded into ``ties``. The naive
identity ``won[a] + won[b] + ties == num_sub_games`` fails any series with a technical loss.

Every row is checked for coherence before it is summed -- a row wins exactly when its scores are
unequal, and the winner is then the higher side. A malformed row is refused by name rather than
crashed on, because a stack trace is not a verdict and both peers need the same one.
"""

from __future__ import annotations

from common.domain.scoring import ZEROED, Outcome, Role, is_tie_row

#: App. F table 17, fixed. Added to EACH side's total on a level series (see module docstring).
TIE_SCORE = 2

class KitSettlementError(Exception):
    """Rows cannot produce a coherent settlement."""


def score_map(row, our_group: str, opponent_group: str) -> dict[str, int]:
    """Map one ledger row's fixed-table scores onto the two group ids by role."""
    if row.role is Role.POLICE:
        return {our_group: row.score_police, opponent_group: row.score_thief}
    return {our_group: row.score_thief, opponent_group: row.score_police}


def result_row(
    *,
    row,
    our_group: str,
    opponent_group: str,
    tokens: dict[str, int],
    log_file: str,
    github_commit: dict | None = None,
) -> dict:
    """Build one result row from one settled ledger row."""
    scores = score_map(row, our_group, opponent_group)
    opponent_role = Role.THIEF if row.role is Role.POLICE else Role.POLICE
    zeroed = row.outcome in ZEROED
    tie = (not zeroed) and is_tie_row(row.outcome, *scores.values())
    winner = None if (zeroed or tie) else max(scores, key=lambda g: scores[g])
    entry = {
        "sub_game_number": row.sub_game_number,
        "roles": {our_group: row.role.value, opponent_group: opponent_role.value},
        "result": row.outcome.value,
        "winner_group": winner,
        "tie": tie,
        "steps": row.steps,
        "tokens": dict(tokens),
        "score": scores,
        "log_files": {our_group: log_file, opponent_group: log_file},
        "audit": {"log_verified": bool(row.audit_ok), "tampered": row.outcome is Outcome.TAMPER_FORFEIT},
    }
    if github_commit:
        entry["github_commit"] = github_commit
    return entry


def _counts(rows: list[dict], groups: tuple[str, str]) -> tuple[dict, dict, int, int]:
    totals = dict.fromkeys(groups, 0)
    won = dict.fromkeys(groups, 0)
    ties = zeroed = 0
    for entry in rows:
        scores = entry.get("score")
        if not isinstance(scores, dict) or set(scores) != set(groups):
            raise KitSettlementError(
                f"sub-game {entry.get('sub_game_number')!r} scores {scores!r}, which is not a "
                f"per-group map over {sorted(groups)} -- a shape fault is refused here rather "
                f"than summed into a total nobody can check"
            )
        for group in groups:
            totals[group] += scores[group]
        winner = entry.get("winner_group")
        level = len(set(scores.values())) == 1
        if (winner is None) != level:
            raise KitSettlementError(
                f"sub-game {entry.get('sub_game_number')!r} declares winner {winner!r} but scores "
                f"{scores} -- a row wins exactly when its scores are unequal, and the winner is "
                f"then the higher side. Two reports that read this differently disagree on a "
                f"result neither side got wrong"
            )
        if set(scores.values()) == {0}:
            zeroed += 1
        elif winner is None:
            ties += 1
        elif winner not in won:
            raise KitSettlementError(
                f"sub-game {entry.get('sub_game_number')!r} names winner {winner!r}, who is not "
                f"one of {sorted(groups)}"
            )
        elif scores[winner] != max(scores.values()):
            raise KitSettlementError(
                f"sub-game {entry.get('sub_game_number')!r} names winner {winner!r}, who did not "
                f"score highest in {scores}"
            )
        else:
            won[winner] += 1
    return totals, won, ties, zeroed


def series_final(
    rows: list[dict],
    groups: tuple[str, str],
    *,
    counted: bool,
    tokens_total: dict[str, int] | None = None,
    games_played: dict[str, int | None] | None = None,
    first_meeting: bool = True,
) -> dict:
    """Derive the whole aggregate from the rows. See the module docstring for the two awards."""
    totals, won, ties, zeroed = _counts(rows, groups)
    series_tie = len(set(totals.values())) == 1
    winner = None if series_tie else max(totals, key=lambda g: totals[g])
    final: dict = {
        "total_score": {g: totals[g] + (TIE_SCORE if series_tie else 0) for g in groups},
        "sub_games_won": won,
        "ties": ties,
        "winner_group": winner,
        "series_tie": series_tie,
    }
    if series_tie:
        final["tie_score_each"] = TIE_SCORE
    if tokens_total is None:
        tokens_total = {g: sum(r["tokens"].get(g, 0) for r in rows) for g in groups}
    final["tokens_total_series"] = tokens_total
    final["games_played_including_this"] = dict(
        games_played if games_played is not None else dict.fromkeys(groups)
    )
    final["first_meeting_between_groups"] = first_meeting
    final["diversity_reward_applied"] = {
        g: bool(counted and first_meeting and winner is not None and g == winner) for g in groups
    }
    return final

# The consensus digest over these rows lives in `kit_consensus`, deliberately apart: it is the
# one hash in this repository that does NOT use the compact canonical form.
