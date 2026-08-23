---
artifact: adr
id: ADR-008
status: accepted
date: 2026-08-23
owners: orchestrator
related_requirements: [SEC-005, SEC-006, OBS-006]
related_tasks: [T033, T034, T047]
supersedes:
---

# ADR-008 — Replay verdict taxonomy, layered coverage, and the trust statement

## Context

The replay verifier at the reviewed baseline collapsed every failed audit to `TAMPERED`, inferred a
half's record shape from the first record, and reported a single binary sense of "verified". Three
separate honesty problems follow from that.

First, a legal-integrity record containing an illegal move was accused of forgery. Forgery and
rule-breaking are different accusations against a peer and must not share one label.

Second, shape was guessed. A half was downgraded because one record looked foreign, and — through
the defect recorded as F-01 — every half was in fact treated as foreign, so payload mutations and
illegal physics were silently accepted.

Third, and most consequential: a matching commitment proves only that the revealed payload matches
that commitment. A party able to rewrite payload, nonce, commitment, result, and manifest together
can produce an unanchored local bundle that is fully internally consistent. Reporting that bundle as
"verified" invites the reader to hear "historically authentic", which the evidence does not support.

## Decision

**Verdicts are distinct and mutually exclusive.** `TAMPERED` means a commitment mismatch or a
withheld committed reveal. `ILLEGAL` means a physics or outcome failure with intact commitments.
`INVALID` means malformed syntax, type, or identity. `INCOMPLETE` means required evidence is absent.
`VERIFIED_OK` means every *available* check passed.

**Coverage is layered, not levelled.** The earlier two-value `FULL` / `INTEGRITY_ONLY` scale is
replaced by a frozen `VerificationCoverage` carrying one independent boolean per layer: `integrity`,
`live_binding`, `physics`, `outcome`, `bundle_digests`, and `external_authenticity`. A supported
foreign shape sets `integrity` true and `physics` false rather than collapsing to a coarse level.
CLI and future GUI adapters print the layers rather than a single adjective.

**Authenticity is never claimed locally.** `external_authenticity` stays false until a peer receipt
or a T018-authorized signature is verified. `VERIFIED_OK` is reported together with that false flag
whenever the bundle is unanchored, and no output describes such a bundle as authentic.

**Offline binding is armed by captured evidence.** `SubgameReplayEvidence` retains the opponent
commitments observed during live play as an ordered immutable tuple, captured after the live audit
has consumed the mutable inbox. Comparing a bundle against that ledger is what makes `live_binding`
meaningful offline; without it there is nothing for a recomputed bundle to disagree with.

**Shape is decoded, never inferred.** Every record is strictly decoded. A mixed shape inside one
half is `INVALID`. The first-record heuristic and the regex shape inference are deleted, not
bypassed.

## Alternatives considered

- **Keep a single `passed` boolean.** Rejected: it is the defect. It cannot distinguish forgery from
  rule-breaking, and it overstates what an unanchored bundle proves.
- **Keep the two-level `FULL` / `INTEGRITY_ONLY` scale.** Rejected: physics, live binding, outcome,
  digests, and signatures become available independently of one another, so any total ordering of
  them either overstates or understates the real coverage.
- **Verify a signature inside the pure verifier.** Rejected: the authoritative signature and receipt
  format is gated behind T018. A future signed-report adapter supplies authenticity without changing
  the pure verifier.
- **Report authenticity optimistically and footnote the caveat.** Rejected: the footnote is exactly
  what a reader skips. The flag is part of the machine-readable report.

## Consequences

Positive: a partner team can act on the difference between "your peer cheated" and "your peer broke
a rule"; the report states precisely which layers were checked; and the honesty of the unanchored
case survives being quoted out of context.

Negative: the report is wider than a boolean, and CLI/GUI adapters must render six booleans. Callers
that expected a single level need updating; that surface is new in this workstream, so no external
consumer is broken.

Verification: replay verification stays pure and filesystem-free, so the taxonomy is exercised by
dense unit tests rather than end-to-end fixtures.

## Validation

- Unit tests map commitment, physics, syntax, and absence to four distinct verdicts, including a
  clean-commitment illegal move that must never be reported as `TAMPERED`.
- A recomputed unanchored bundle is proven internally consistent and simultaneously reported with
  `external_authenticity=false`.
- A recomputed bundle compared against the peer-observed commitment ledger is detected as diverging.
- Foreign-shape evidence sets `integrity` true with `physics` and `live_binding` false.
- `scripts/replay.py` and the sanitized transcripts under `docs/evidence/replay/` show the layers.

## Approval

- Decision owner: orchestrator
- Approved by: orchestrator (ORC-R0)
- Approval date: 2026-08-23
