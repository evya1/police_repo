---
artifact: adr
id: ADR-013
status: accepted
date: 2026-08-24
owners: orchestrator
related_requirements: [REPORT-005, REPORT-006, REPORT-007, OBS-006, SEC-005, SEC-006, LEAGUE-002, LEAGUE-003]
related_tasks: [T057, T058]
supersedes:
---

# ADR-013 — Identity is declared, agreement is derived, and nothing is invented either way

## Context

Wave 1 (ADR-012, T056) projects a settled series into the kit's 14-artifact bundle, but two
things in that bundle were still placeholders: the declaration's `groups` block named nothing
about either team beyond a bare `group_id`, and the result's `mutual_agreement` block was never
actually confirmed between peers — it was a locally-computed digest with no counter-proposal
behind it.

Both gaps have the same shape: a value that is either **honestly declared and verifiable**, or
**honestly absent**. Nothing here may be filled with a placeholder that would look, byte for
byte, like a group that actually supplied that evidence (App. E rules 37–38).

## Decision

**Identity** (`common/transport/kit_identity.py`) is a per-group, signed declaration block.
The signature is sign-then-insert: the digest covers the block *before* the `signature` key
exists, so the field is excluded from its own preimage — a different construction from the
consensus digest (ADR-012/DEC-4), which is bare. Identity is never inside the consensus scope:
a per-side value inside a shared preimage would make two honest peers unable to agree on
anything (a per-side value differs by construction, so the digests would never match).

The greeting (`common/transport/negotiate.py::our_greeting`) gained an **additive**
`identity_block` parameter. Every pre-existing golden vector under `tests/contract/vectors/`
still passes byte-for-byte with no argument supplied — the extension is opt-in, and
`verify_greeting` never refuses on a missing, partial, or unknown identity field (SPEC §7:
refuse only when both sides declare and disagree).

**Result agreement** (`common/transport/kit_agreement.py`) compares only the consensus digest
(ADR-012's `consensus_sha256`) between the two sides' proposals. Equal digests agree; anything
else — a different digest, or no counter-proposal at all — does not, and the reason names what
happened. `assert_reportable` raises `NotAgreed` when a **counted** series reaches reporting
without agreement; a warm-up owes no report and is never blocked. No sanction beyond "the
report is not sent" is invented — the actual missing-report penalty is an open question with
the course staff (OPEN-004).

**Counted-play readiness** (`src/police_peer/evidence/identity_source.py::assert_counted_ready`)
refuses *before any game starts* when a counted series could not honestly be reported: an
incomplete identity, an unavailable Git commit, an uncomputable config digest, no configured
Step-0 signer, unknown counted token usage, or a pairing the league guard rejects (App. F
table 18, App. E rule 52). Warm-up mode never refuses on any of these.

## Consequences

* `counted_games_played` (declaration, exclusive of the series about to be played) and
  `games_played_including_this` (result, inclusive) must satisfy `inclusive == exclusive + 1`
  for a counted series (DEC-11). An opponent count we never learned is `null`, never `0`.
* The opponent's identity block in a published declaration carries only what their own greeting
  actually declared (DEC-12). This project's wire layer does not yet persist a captured
  opponent identity block outside the handshake closure that verifies it — a declaration built
  today therefore falls back to a bare `{"group_id": ...}` for the opponent side unless the
  caller supplies a captured block explicitly. Threading that capture through
  `common/transport/opponent_pin.py` (or an equivalent series-owned store) without touching
  Wave-1/Wave-2's frozen `common/` modules is left open for a follow-up task; nothing is
  fabricated in the meantime.
* This codebase has no configured Step-0 signing credential yet (INPUT-003: no course-supplied
  credential observed), so `assert_counted_ready` refuses counted play unconditionally until
  one is wired in. This is the correct, honest DEC-10 behaviour, not a regression: the same
  fail-closed rule already governs `evidence/step_zero.py`.
