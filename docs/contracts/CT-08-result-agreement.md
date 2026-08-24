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

C06 (Reporting & League). The comparison itself lives in `common/transport/kit_agreement.py`
so both peers decide agreement by identical code.

## Consumers

The reporting root, which may not transmit without an agreement; the result artifact, whose
`mutual_agreement.confirmed` reports whether one was actually reached.

## Input

Our settled rows and derived aggregate, plus the opponent's proposal message (or its absence).

## Output

`AgreementOutcome(agreed: bool, reason: str, their_sha: str | None)`.

## Wire message

```json
{
  "kind": "result_agreement",
  "game_id": "<sorted pair>",
  "game_uid": "<uuid>",
  "consensus_sha256": "<hex>",
  "final_result": { "...": "the aggregate, so a dispute is diffable" }
}
```

The digest is the claim. `final_result` rides along so a disagreeing opponent can see *what*
we settled on rather than only *that* we disagree; it is never what agreement is decided on.

## Externally visible invariants

- Agreement is decided on `consensus_sha256` alone.
- A missing counter-proposal is **not** agreement. A timeout is not assent.
- Two different `game_uid`s never agree, whatever the digests say — that is the contradiction
  App. E rule 35 zeroes both teams for.
- `assert_reportable` refuses a counted series that was never agreed, and invents no sanction
  (OPEN-004 is unresolved).
- A warm-up owes no report and therefore never refuses.
- `mutual_agreement.confirmed` is `true` only when an opponent actually confirmed. A result
  that claims an agreement which did not happen is worse than one that admits it is unsettled,
  because the opponent's report will say so.

## Verification

`tests/contract/kit_artifacts/test_kit_agreement.py`; end-to-end in
`tests/integration/test_mutual_agreement_settles.py`, which requires both peers to emit a
byte-identical `mutual_agreement.sha256`.
