---
artifact: contract
id: CT-05
status: draft
owner_component: C04
shared: true
updated: 2026-08-15
---

# CT-05 — Observability Event Projection

## Owner

C04 (Runtime & Reliability), sourcing state from C01 where the event concerns board/turn state.

## Consumers

C05 (Observability & Replay) — the GUI and Replay Viewer render only what this contract exposes.

## Input

An internal lifecycle-state transition, a turn-lock signal, or a belief-snapshot update (from C02).

## Output

A typed observability event: `{kind: lifecycle | turn_lock | belief_update, local_truth_payload}`.

## Externally visible invariants

- **No event ever carries the opponent's true position, an unrevealed Nonce, or a credential.** This is the single most important invariant in the system for OBS-002 compliance — the projection boundary exists specifically to make that leak structurally impossible rather than merely policy-forbidden.
- Every event is derived only from this peer's own local state.
- Turn-lock events fire exactly at Commit-send and exactly at next-turn-received (OBS-004).

## Failure/error behavior

An event that cannot be safely redacted (e.g. a malformed internal state) is dropped rather than emitted in a possibly-leaking form; the GUI shows a stale/loading state instead.

## Version / compatibility

Additive-only; a new event `kind` may be added without breaking existing consumers.

## Governing requirement IDs

OBS-001…004.

## Police/Thief identity requirement

**Yes** — the projection shape is identical; what differs is only the GUI rendering built on top of it (role-specific PLAN concern, not part of this contract).
