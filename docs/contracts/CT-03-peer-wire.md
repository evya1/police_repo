---
artifact: contract
id: CT-03
status: draft
owner_component: C03
shared: true
updated: 2026-08-15
---

# CT-03 — Peer Wire Envelope & Tool Surface

## Owner

C03 (Peer Protocol & Integrity).

## Consumers

C04 (Runtime & Reliability) — retries/times out requests carried on this envelope.

## Input

An outbound tool call from the local Orchestrator (C04), or an inbound FastMCP frame from the sibling peer.

## Output

A validated, deadline-stamped envelope on the wire; on the receiving side, a parsed and validated request/response handed to C04's state machine.

## Externally visible invariants

- Every request carries a timestamp and expiry deadline (NET-005 field, carried here; the retry/timeout decision itself is C04's).
- The verbal-hint field is always free-form text (NET-003); no numeric-position substitute field exists (NET-004).
- Exact duplicate frames are recognized and absorbed without reapplying side effects.

## Failure/error behavior

Expiry: the envelope's deadline field is what C04 reads to decide retry vs. technical loss — this contract does not itself decide. Malformed/unparseable frame: rejected with no partial state applied. Bounded reordering: buffered until predecessor within the configured window, rejected beyond it.

## Version / compatibility

Negotiated and versioned per CFG-001's locked shared contract; the exact tool names/envelope fields are this project's own engineering choice (non-official pending OPEN-001/OPEN-007), versioned so an eventual official schema can be adopted without an incompatible break.

## Governing requirement IDs

NET-001…004; NET-005 (carrier of the deadline field only — the reliability behavior is owned by C04).

## Police/Thief identity requirement

**Yes** — the two peers must speak the identical wire shape for FastMCP calls to succeed at all.
