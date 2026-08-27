"""Mutual result agreement, and the refusal that protects both peers (CT-08, ADR-013).

App. E rule 35 is unusually harsh: two counted reports that contradict each other score **zero
for both teams**, including the side that got everything right. So the expensive failure is not
disagreeing -- it is reporting a disagreement without noticing. This module makes noticing
structural.

Agreement is decided on ONE value: the consensus digest from ``kit_consensus``. That digest
covers exactly what two honest peers must produce identically and nothing they may legitimately
differ on, so comparing anything else would manufacture disputes. Equal digests agree. Different
digests do not, and the reason names both so a human can diff the two scopes rather than guess.
Silence does not agree either -- an opponent who never answered has not confirmed anything, and
treating a timeout as assent is how one side ends up reporting alone.

``assert_reportable`` is the gate. A counted series that has not agreed does not get to send a
report. That is a refusal to act, not a sanction: what the missing-report penalty actually is
remains an open question with the course staff (OPEN-004), and this module does not invent one.
"""

from __future__ import annotations

from dataclasses import dataclass

from common.transport.kit_consensus import consensus_scope, consensus_sha256

#: The wire message kind. Anything else on this channel is not an agreement proposal.
AGREEMENT_KIND = "result_agreement"


class NotAgreedError(Exception):
    """A counted series reached reporting without a mutual agreement."""


@dataclass(frozen=True, slots=True)
class AgreementProposal:
    """Our settled view of the series, and the digest that stands for it."""

    game_id: str
    game_uid: str
    consensus_sha256: str
    final_result: dict
    rows: list[dict]


@dataclass(frozen=True, slots=True)
class AgreementOutcome:
    """Whether the two peers settled on one result, and why not when they did not."""

    agreed: bool
    reason: str
    their_sha: str | None = None
    rows: list[dict] | None = None
    final_result: dict | None = None
    tokens_by_sub_game: dict[int, dict[str, int]] | None = None


def build_proposal(game_id: str, game_uid: str, final_result: dict, rows: list[dict]):
    """Build our proposal from the settled rows."""
    scope = consensus_scope(game_id, final_result, rows)
    return AgreementProposal(
        game_id=game_id,
        game_uid=game_uid,
        consensus_sha256=consensus_sha256(scope),
        final_result=final_result,
        rows=rows,
    )


def proposal_wire(proposal: AgreementProposal, *, sender: str | None = None) -> dict:
    """The message we put on the wire.

    The digest is the claim; the aggregate rides along so a disagreeing opponent can see WHAT
    we settled on rather than only that we disagree. It is never what agreement is decided on.
    """
    message = {
        "kind": AGREEMENT_KIND,
        "game_id": proposal.game_id,
        "game_uid": proposal.game_uid,
        "consensus_sha256": proposal.consensus_sha256,
        "final_result": proposal.final_result,
    }
    if sender is not None:
        message["sender"] = sender
    return message


def evaluate(ours: AgreementProposal, theirs: dict | None) -> AgreementOutcome:
    """Compare our proposal with the opponent's, or report why we cannot."""
    if not isinstance(theirs, dict):
        return AgreementOutcome(False, "no counter-proposal arrived, so nothing was agreed")
    if theirs.get("kind") != AGREEMENT_KIND:
        return AgreementOutcome(
            False, f"expected a {AGREEMENT_KIND!r} message, got {theirs.get('kind')!r}"
        )
    their_sha = theirs.get("consensus_sha256")
    if not isinstance(their_sha, str) or not their_sha:
        return AgreementOutcome(False, "the counter-proposal declared no consensus digest")
    if theirs.get("game_id") != ours.game_id:
        return AgreementOutcome(
            False,
            f"the counter-proposal names game_id {theirs.get('game_id')!r}, we derived "
            f"{ours.game_id!r}",
            their_sha,
        )
    if theirs.get("game_uid") != ours.game_uid:
        return AgreementOutcome(
            False,
            f"the counter-proposal names game_uid {theirs.get('game_uid')!r}, we derived "
            f"{ours.game_uid} -- two uids for one match is the contradiction rule 35 zeroes",
            their_sha,
        )
    if their_sha == ours.consensus_sha256:
        return AgreementOutcome(True, "both peers derived one consensus digest", their_sha)
    return AgreementOutcome(
        False,
        f"consensus digests differ: we derived {ours.consensus_sha256}, they declared "
        f"{their_sha}. Diff the signed scope (aggregate plus the five-key rows) before either "
        f"side reports -- two contradictory reports score zero for BOTH teams",
        their_sha,
    )


def assert_reportable(outcome: AgreementOutcome, *, counted: bool) -> None:
    """Refuse to report a counted series that was never agreed.

    A warm-up owes no report, so it passes regardless. This raises rather than inventing a
    sanction: the penalty for a missing report is an open question with the course staff, and
    guessing at one would be worse than declining to send.
    """
    if counted and not outcome.agreed:
        raise NotAgreedError(
            f"this counted series has no mutual agreement, so no report is owed or sent: "
            f"{outcome.reason}"
        )
