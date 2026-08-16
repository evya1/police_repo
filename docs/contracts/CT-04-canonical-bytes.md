---
artifact: contract
id: CT-04
status: operational-convention
owner_component: C03
shared: true
updated: 2026-08-16
---

# CT-04 — Canonical Bytes & Commitment Preimage

## Owner

C03 (Peer Protocol & Integrity), specifically M-05 (Commit-Reveal & Audit).

## Consumers

C06 (Reporting & League) — embeds the resulting commitment/hash values in signed report artifacts without recomputing the canonicalization itself.

## Input

A step's `{State, Move, Intent, Nonce}` tuple (minimum binding per SEC-003) plus any additional fields the eventual official schema requires.

## Output

A canonical byte sequence suitable for SHA-256 hashing, and the resulting commitment hash.

## Status of this contract

The official byte contract has not been supplied (OPEN-001, OPEN-007) and both items remain `official_status: OPEN`. The rules below are an **operational convention**: binding for this implementation because two peers cannot verify each other without one deterministic byte form, verified by committed golden vectors, and replaced at this same boundary when an official schema arrives. Nothing here may be described as the officially required byte contract.

## Canonical serialization

- UTF-8 encoding, no byte-order mark.
- Object keys sorted by Unicode code point, ascending.
- Compact separators: `,` between items and `:` between key and value, with no other whitespace.
- Non-ASCII characters emitted literally, never as `\u` escapes.
- Floats use the shortest representation that round-trips exactly; a value that fails shortest round-trip is rejected rather than silently re-formatted.
- Integers and floats stay distinct; an integral float is not narrowed to an integer.
- No trailing newline.

## Commitment construction

`commit = SHA-256( canonical(payload) || "|" || nonce )`, where `payload` is the `{State, Move, Intent}` triple in the canonical form above, `||` is byte concatenation, `"|"` is the single byte U+007C, and `nonce` is the step's fresh nonce in its transmitted textual form.

The digest is carried and compared as a 64-character **lowercase** hexadecimal string. Uppercase is a mismatch, because the value is compared as a string.

The same construction produces the sealed-terms and identifier signatures built on top of it; there is exactly one canonicalization path in the repository and no parallel serializer.

## Ordering

1. `commit` for a step is sent before the step is revealed.
2. Acknowledgement of the received commitment precedes reveal.
3. Reveal discloses `{State, Move, Intent, Nonce}` for that step.
4. The full audit runs only after the last reveal of a sub-game.

The nonce is never included in any transmitted or logged representation before the audit phase (SEC-004). Replay follows recorded step order.

## Externally visible invariants

- The same logical tuple always canonicalizes to the same bytes on both peers — the entire point of this contract.
- Two independent peers running the committed vectors produce identical verification results.
- A missing, extra, reordered, or mutated step is detected during audit.

## Failure/error behavior

A canonicalization or commitment mismatch during audit is an integrity failure: it yields an immutable TAMPERED verdict with no repair path. A mismatch found by the local vector suite is a test failure to be diagnosed, not a game-scoring event.

## Verification

Deterministic golden vectors committed under T008 cover, at minimum:

- key ordering, compact separators, literal non-ASCII output, and absence of a trailing newline;
- Unicode payloads including non-BMP characters;
- float shortest round-trip acceptance and the rejection of a value that fails it;
- the commitment construction including the single-pipe nonce separator and lowercase hex output;
- commit/acknowledge/reveal/audit ordering, and the rejection of an out-of-order reveal;
- tamper detection for a one-byte mutation of state, move, intent, or nonce;
- replay and step-order verification for a full sub-game.

Both role repositories run the same vectors. Differential fixtures for compact-versus-spaced JSON, nonce-inside versus nonce-appended, and alternative signature-insertion orders are retained as rejection tests, not as selectable production behavior.

## Version / compatibility

Versioned so an official schema can replace this convention at the adapter boundary without an incompatible break. No counted match uses this convention as its production canonicalization once an official contract exists.

## Governing requirement IDs

SEC-001…005.

## Police/Thief identity requirement

**Yes, and byte-for-byte** — this is the one contract where "close enough" is a correctness failure.
