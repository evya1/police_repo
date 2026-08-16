---
artifact: component-plan
id: PLAN-C02-POLICE
component: C02
status: draft
derived_from: PRD-C02
owner: orchestrator
updated: 2026-08-16
---

# C02 — Perception & Strategy (Police PLAN)

## Approach summary

`src/police_peer/scent/` implements the shared, byte-identical scent model (M-01) as one small interface with two supported profiles behind it. `src/police_peer/belief/` implements the shared belief invariants (M-02) and consumes whichever profile is selected through that interface, never branching on model identity. `src/police_peer/strategy/` implements Police-specific pursuit policy (M-03), isolated from the optional verbal-hint provider by the same module boundary that satisfies ARCH-007.

## Internal design

- `scent/model.py` — the small common scent-model interface and the configuration-driven selection of the active profile; pure functions of position and prior field, defaulting to `subtractive_chebyshev_v1` (ADR-004).
- `scent/profiles/` — the two concrete supported profiles, `subtractive_chebyshev_v1` and `multiplicative_book_v1`, each implemented exactly as M-01 §B specifies. They are separate implementations on purpose: the two differ in decay form, update order, rounding, upper clamp, and transport, so deriving one from the other would be a defect.
- `scent/lock.py` — pre-series model-lock record (STRAT-005): builds the selected profile's pinned parameter document, hashes it, and exposes the declaration for the handshake. It no longer waits on an official OPEN-009 answer; the approved profile is sufficient to lock.
- `belief/` — normalized distribution update from scent + hints; property-tested against M-02's three invariants.
- `strategy/` — Police pursuit policy (see `docs/mechanisms/M-03-police-strategy.md`) selecting from C01's legal-action set via CT-02.
- `strategy/providers/` — optional P2 language-model text adapter (T027 only), provider-neutral, never in the movement-decision path.

## State/responsibility ownership

Scent and belief are pure computation over transmitted/local data; strategy owns the final action selection but never the domain legality check itself (that stays in C01).

## Local test strategy

Numeric scent vectors (M-01's worked example, non-saturating range) plus a conformance-vector suite for **each** registered profile, including repeated-emission/saturation, edges, corners, and clipping; a determinism check that the same pinned parameter document always hashes identically; belief property tests (M-02's three invariants); seeded strategy tests against fixed opponent-position fixtures (test doubles, not the real Thief peer); mocked optional-provider success/failure/timeout with deterministic-fallback assertions.

## Component-level integration

Strategy consumes C01's legal-action set through CT-01 (read-only) and hands its decision to C04 through CT-02. No live network dependency for local testing.

## Known risks

The approved default profile being mistaken for an official resolution of OPEN-009 — mitigated by the authority-boundary section of ADR-004 and the split between M-01 §A and §B. Profile selection leaking outward as `if model == ...` branches in belief or strategy rather than staying behind the scent interface. Strategy complexity creeping into a general-purpose planner rather than the bounded pursuit policy M-03 actually specifies.
