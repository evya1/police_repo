---
artifact: component-prd
id: PRD-C06
component: C06
status: draft
shared: true
owner: orchestrator
updated: 2026-08-15
---

# C06 — Reporting & League

## Purpose

Own the official machine-readable artifacts, the send-only Gmail pipeline behind a central Gatekeeper, and the six-sub-game series/scoring/pairing-eligibility mechanics. This component turns a verified match result into the auditable evidence the lecturer actually receives.

## Requirements owned (primary)

REPORT-001…013 (independent automatic sending, official recipient, send-only OAuth scope, local-only secret files, signed JSON artifacts, the four artifact schemas, rate limiting, DOS detection, backoff, daily quota); LEAGUE-001…007 (six-sub-game series, eligibility limits, single-count-per-opponent, honest prior-match declaration, diversity reward, tie score, fairness-evidence provision); QR-008, QR-018 (central external-service Gatekeeper; paid-API cost documentation). 22 requirements total.

## Requirements consumed / affected

- REPORT-005…009, GAME-013 (C03/C01): reports summarize C03's verified audit result and C01's score, never recompute or override them.
- CFG-009, CFG-010 (C01): the reported Git commit id per game is consumed here; C01 owns the configuration-lifecycle rule that produces it.
- SEC-009 (C03): per-series token totals consumed into the result report; C03 owns the metering and its cryptographic lock.
- SEC-010 (system): OAuth secret handling is a repository-wide prohibition this component must respect, not a behavior it defines.

## Observable behavior

- At the end of every legal game, each team independently and automatically sends a separate final report via Gmail API to the official recipient (REPORT-001, REPORT-002), using `gmail.send`-only OAuth scope with local-only `credentials.json`/`token.json` (REPORT-003, REPORT-004).
- The report is a uniform, signed, machine-readable JSON attachment — never plaintext (REPORT-005) — using the four official artifact filenames and a common identifier (REPORT-006, REPORT-007), including repository links, per-sub-game Git commit, and token totals (REPORT-008).
- Both teams agree on the result and send consistent separate reports (REPORT-009); missing or
  conflicting evidence is preserved and reporting is refused.
- Sending is protected by a Token Bucket rate limiter (REPORT-010), a DOS detector that can lock the pipeline (REPORT-011), HTTP 429 backoff rather than blind retry (REPORT-012), and ideally a daily quota manager (REPORT-013).
- A counted series against one opponent contains exactly six sub-games (LEAGUE-001); at least two counted matches against different teams and no more than ten total are required (LEAGUE-002); only one match per opponent counts (LEAGUE-003); each team accurately declares its prior counted-match count (LEAGUE-004); a new-opponent win earns the fixed diversity reward of 10 (LEAGUE-005); a cumulative tie gives 2 to each side (LEAGUE-006); hardware/version/token evidence is provided for lecturer-side fairness normalization without inventing a local formula (LEAGUE-007).

## Inputs

A verified sub-game result (from C04/C03, via CT-06); the locked configuration (from C01); series/eligibility state.

## Outputs

Four signed JSON artifacts per the official schema (once OPEN-001 resolves); a sent Gmail message; series scoring and pairing-eligibility verdicts.

## Invariants

- No plaintext report is ever accepted as satisfying REPORT-005.
- Every external call in this component passes through the central Gatekeeper (QR-008) — no direct Gmail or provider call from report/strategy code.
- Live sending never occurs in a test; tests use doubles.

## Constraints

- The official JSON schemas are never synthesized (NG-004); until OPEN-001 resolves, this component works only against the internal draft contract and differential tests.

## Failure cases

- Gmail 429/quota exhaustion: Gatekeeper backoff/queue or explicit unsent failure, never a blind retry.
- Missing or conflicting report from the opponent: preserve the evidence and refuse automatic
  scoring or transmission.
- A declared prior-match count found false: disqualification per LEAGUE-004.

## Edge cases

- A tie score interacting with the still-open series-add-vs-replace aggregation question (OPEN-008).
- A ninth or tenth counted match approaching the LEAGUE-002 ceiling.

## Acceptance scenarios

- [ ] Official-schema artifact generation is exercised only once OPEN-001 resolves; until then only differential/draft-contract tests run. {#schema_adoption}
- [ ] A mocked Gmail pipeline enforces rate limiting, DOS lockout, and 429 backoff without a live call. {#gatekeeper_pipeline}
- [ ] Series aggregation and tie handling are exercised as differential tests pending OPEN-008; the fixed six-sub-game count and GAME-013 score table are asserted directly. {#series_aggregation}
- [ ] Report-refusal sanction is exercised only once OPEN-004 resolves. {#sanction_settlement}
- [ ] Pairing-eligibility preflight passes only with real opponent/endpoint data present. {#pairing_preflight}

## Relevant contracts

`planning/contracts/CT-04-canonical-bytes.md` (consumer); `planning/contracts/CT-06-verified-result.md` (consumer).

## Relevant OPEN/input gates

- OPEN-001 — `blocks: start` on schema-adoption work (T016) specifically, since NG-004 forbids any substitute.
- OPEN-004 — `blocks: criterion` on `{#sanction_settlement}`.
- OPEN-008 — `blocks: criterion` on `{#series_aggregation}`.
- `G-LIVE` — `blocks: criterion` on `{#pairing_preflight}`.

## Definition of Done

Internal design deferred to the component PLAN, authored when T016–T020 are claimed. This PRD's five acceptance scenarios and the REPORT-*/LEAGUE-*/QR-008,018 ownership are the fixed contract that PLAN must satisfy.
