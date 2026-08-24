---
artifact: contract
id: CT-08
status: draft
owner_component: C06 (Reporting & League)
shared: true
updated: 2026-08-24
---

# CT-08 — Result Agreement

## Owner

C06 (Reporting & League). The pure contract lives in the shared transport layer
(`common/transport/kit_agreement.py`, `common/transport/kit_identity.py`) so both role
repositories agree byte-for-byte on what "agreed" means; the wire exchange is per-role
(`src/{police_peer,thief_peer}/wire/result_agreement.py`).

## Consumers

Both peers, once per settled series, before a counted result is ever transmitted. The kit
bundle's `mutual_agreement.confirmed` field records the outcome for a third-party reader.

## Input

Each side's own `AgreementProposal` (`game_id`, `game_uid`, `consensus_sha256`, `final_result`,
`rows`), built from the same settled rows CT-07's `series_final`/`kit_consensus` already
derive.

## Output

An `AgreementOutcome`: `agreed: bool`, a human-readable `reason`, and the opponent's declared
`their_sha` when one arrived at all.

## Rule

Agreement compares **only** `consensus_sha256` — the same bare, spaced-separator digest CT-07
already computes (ADR-012 DEC-4). Equal digests agree. A different digest, a message of the
wrong kind, or no counter-proposal at all does not agree, and the reason says which. Nothing
about *why* two peers disagree is inferred here — a disagreeing pair gets a report that names
both digests, not a diagnosis.

## Enforcement

`assert_reportable(outcome, counted=...)` raises `NotAgreed` when a counted series has no
agreement. A warm-up owes no report and always passes. The wire exchange
(`wire/result_agreement.py::exchange`) sends our proposal exactly once over the existing
control channel, waits for the opponent's within a fixed budget, and never raises into the game
loop — a timeout or a malformed reply is `AgreementOutcome(agreed=False, ...)`, not an
exception, so the series' own reporting path decides what a non-agreement means for it.

## Prohibited

No sanction beyond "the report is not sent" — the actual penalty for a missing report is an
open question with the course staff (OPEN-004). No retry loop beyond whatever the channel's own
transport layer already provides. Identity (CT-08's sibling declaration, ADR-013) never enters
the consensus scope this contract compares.
