---
artifact: contract
id: CT-02
status: draft
owner_component: C02
shared: true
updated: 2026-08-15
---

# CT-02 — Strategy Decision Request/Response

## Owner

C02 (Perception & Strategy).

## Consumers

C04 (Runtime & Reliability) — sequences the selected action into the Commit-Reveal cycle.

## Input

A decision request: current legal-action set (from CT-01), current belief snapshot (M-02), latest received hint text, latest received opponent scent field.

## Output

A selected legal action (one member of the CT-01 legal-action set) and an outgoing hint string (template or, if configured, provider-generated per STRAT-008).

## Externally visible invariants

- The selected action is always a member of the legal-action set CT-01 provided this turn; strategy never invents an action.
- Movement selection never depends on an unvalidated external model call (NG-003, STRAT-008); any LLM involvement is limited to hint text/behavioral analysis by default.
- The outgoing hint is free-form natural language (NET-003), never a disguised coordinate (NET-004).

## Failure/error behavior

A decision-request timeout (e.g. an optional provider call exceeding its budget) falls back to the already-selected legal action and a bounded deterministic template hint — it never blocks the turn indefinitely.

## Version / compatibility

Additive-only on the request/response shape.

## Governing requirement IDs

ARCH-007, STRAT-007.

## Police/Thief identity requirement

**Yes** for the contract shape (both roles expose the same request/response fields); the decision policy inside is role-specific (M-03/M-04) and is not part of this contract.
