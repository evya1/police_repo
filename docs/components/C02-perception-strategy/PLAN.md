---
artifact: component-plan
id: PLAN-C02-POLICE
component: C02
status: draft
derived_from: PRD-C02
owner: orchestrator
updated: 2026-08-15
---

# C02 — Perception & Strategy (Police PLAN)

## Approach summary

`src/police_peer/scent/` implements the shared, byte-identical scent model (M-01). `src/police_peer/belief/` implements the shared belief invariants (M-02). `src/police_peer/strategy/` implements Police-specific pursuit policy (M-03), isolated from the optional verbal-hint provider by the same module boundary that satisfies ARCH-007.

## Internal design

- `scent/model.py` — the locked recurrence and emission; pure function of position and prior field.
- `scent/lock.py` — pre-series model-lock record (STRAT-005); records the agreed numeric example and a cryptographic lock hash once OPEN-009 resolves.
- `belief/` — normalized distribution update from scent + hints; property-tested against M-02's three invariants.
- `strategy/` — Police pursuit policy (see `docs/mechanisms/M-03-police-strategy.md`) selecting from C01's legal-action set via CT-02.
- `strategy/providers/` — optional P2 language-model text adapter (T027 only), provider-neutral, never in the movement-decision path.

## State/responsibility ownership

Scent and belief are pure computation over transmitted/local data; strategy owns the final action selection but never the domain legality check itself (that stays in C01).

## Local test strategy

Numeric scent vectors (M-01's worked example, non-saturating range); belief property tests (M-02's three invariants); seeded strategy tests against fixed opponent-position fixtures (test doubles, not the real Thief peer); mocked optional-provider success/failure/timeout with deterministic-fallback assertions.

## Component-level integration

Strategy consumes C01's legal-action set through CT-01 (read-only) and hands its decision to C04 through CT-02. No live network dependency for local testing.

## Known risks

Scent saturation ambiguity (OPEN-009) tempting a premature production default — mitigated by the differential-test-only rule in M-01. Strategy complexity creeping into a general-purpose planner rather than the bounded pursuit policy M-03 actually specifies.
