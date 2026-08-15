---
artifact: contract
id: CT-04
status: draft — non-official
owner_component: C03
shared: true
updated: 2026-08-15
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

## Externally visible invariants

- The same logical tuple always canonicalizes to the same bytes on both peers (the entire point of this contract).
- The Nonce is never included in any transmitted or logged representation before the audit phase (SEC-004).

## Failure/error behavior

A canonicalization mismatch between peers is a TAMPERED-equivalent integrity failure once this contract is promoted to official status; while in draft status it is a test failure to be diagnosed, not a game-scoring event.

## Version / compatibility

**Explicitly non-official draft, gated by OPEN-007.** This contract's exact byte shape (Nonce placement, Unicode escaping, key/field separators, signature-field insertion order) is an internal engineering choice, exercised only through the compatibility decision matrix in `planning/mechanisms/M-05-commit-reveal-integrity.md`, and is superseded without ceremony the moment an official schema (via OPEN-001/INPUT-001) resolves OPEN-007. No counted match may use this draft contract as its production canonicalization.

## Governing requirement IDs

SEC-001…005.

## Police/Thief identity requirement

**Yes, and byte-for-byte** — this is the one contract where "close enough" is a correctness failure; it is the reason OPEN-007 is treated as a hard blocker on cross-peer fixtures specifically.
