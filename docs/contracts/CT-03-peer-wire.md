---
artifact: contract
id: CT-03
status: draft
owner_component: C03
shared: true
updated: 2026-08-16
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

## Default interoperability profile — `reference-v3`

This project's default adapter profile, adopted as an operational convention by `ADR-004` (`docs/decisions/`). It is not an official schema — it does not resolve OPEN-001 or OPEN-007, and any officially compliant peer stays a valid opponent behind the same adapter boundary.

### Required tool surface and argument names

| Tool | Required | Argument name | Carries |
|---|---|---|---|
| `negotiate` | yes | `message` | The pre-game gate: flat terms, nonce, signature, identity. Either side may open |
| `receive_turn` | yes | `message` | One turn message per half-turn. **Each side calls the other's `receive_turn`** — the transport is symmetric push, so neither peer can be purely passive |
| `submit_audit` | yes | **`payload`** | One audit payload per sub-game: the full sealed chain plus nonces, for the opponent to re-hash |
| `receive_control` | optional | `message` | A status channel that touches no game state and is never sealed or scored |

**The argument-name asymmetry is load-bearing and must be preserved.** `submit_audit` takes `payload`; the other three take `message`. A peer that sends `message` to `submit_audit` fails schema validation at the exact moment both sides are trying to agree on a result.

There is no step-0 tool and no step-0 turn on this profile: the hardware/model declaration rides in `negotiate` under `identity`, and the sealed step-0 record is disclosed inside `submit_audit`. There is no `hello` tool; liveness is a tool listing, not a tool call.

### Turn-message requirements

Required keys: `step`, `sender`, `hint`, `smell_grid`, `commit`, `timestamp`. Optional: `barrier_placed`, `capture_claim`, `claim_response`, `win_claim`.

- **`smell_grid` is a required key on this profile and must be preserved.** Its shape is `{'r,c': number}`; a stringified intensity is refused. Under `reference-v3` the grid is transmitted, which is why the default scent profile in M-01 §B.1 is the transmitted one.
- `commit` is 64-char lowercase hex; uppercase is a divergence because the value is compared as a string.
- `timestamp` is decorative in content but must be non-empty.
- A missing required key is refused, never defaulted.
- An unknown key is tolerated and ignored — that is the extension seam.
- Every one of these decisions is made **before** any state change; a partially applied bad turn cannot be rolled back.

### Locked-model declarations

Profile choices are declared as a hash over a pinned parameter document, sent at negotiate time as `<family>_sha256`, for the families `scent_model`, `wire_shape`, `info_mode`, and `smell_binding`. The document itself never crosses the wire — only the hash — so the pinned field set is what makes two independent implementations' declarations comparable.

These declarations sit **outside** the closed signed-terms set. The signed terms are a flat, closed key list; adding a profile key to them would break the signature, which is precisely why the separate declaration mechanism exists.

**Refusal rule:** refuse only when both peers declare a family and the declared hashes disagree. Omission is never refusal — one side declaring while the other is silent still plays.

### Our declared profile values

| Family | Our value |
|---|---|
| `wire_shape` | `reference-v3` |
| `scent_model` | `subtractive_chebyshev_v1` (default; `multiplicative_book_v1` also supported and selectable) |
| `info_mode` | `belief` — the rival's position is outside the observation space; under `reference-v3` this is structural, because the rival's position never crosses the wire |
| `smell_binding` | current/unbound; `commit_grid_v1` is excluded from the approved profile because it changes the commitment preimage |

### Turn order

`reference-v3` fixes the turn-order convention explicitly: **the thief takes the first game turn.** The `wire_shape` declaration does not cover turn order, so a matching lock can actively confirm agreement while hiding this exact disagreement — two peers that each expect the other to move first both wait forever after a fully successful handshake. This convention is therefore recorded here explicitly and must be preserved.

### Sender / receiver roles and local operation

Each peer runs its own server and dials the other's; a peer that only listens never plays. The whole profile is exercisable as two local processes with no public endpoint, no tunnel, and no real opponent URL. Live endpoint and tunnel selection remain PLANQ-006 and later tasks.

## Governing requirement IDs

NET-001…004; NET-005 (carrier of the deadline field only — the reliability behavior is owned by C04).

## Police/Thief identity requirement

**Yes** — the two peers must speak the identical wire shape for FastMCP calls to succeed at all.
