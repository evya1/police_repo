---
artifact: contract
id: CT-06
status: draft
owner_component: C03 / C04 (co-owned — C03 verifies, C04 finalizes)
shared: true
updated: 2026-08-15
---

# CT-06 — Verified Sub-Game Result

## Owner

Co-owned: C03 (M-05) produces the audit verdict; C04 attaches it to the terminal lifecycle state that closes the sub-game.

## Consumers

C06 (Reporting & League) — settles and reports only a result that has passed through this contract; C05 (Observability & Replay) — displays the same verdict via CT-05.

## Input

A completed sub-game's full step log plus the final mutual audit outcome (SEC-005/SEC-006).

## Output

`{sub_game_id, outcome: CAPTURE | SURVIVAL | TECHNICAL_LOSS | TAMPERED, score: {police, thief}, verified: bool}`.

## Externally visible invariants

- `verified: true` is set only after a complete mutual audit with no hash mismatch (SEC-005, SEC-006).
- A `TAMPERED` outcome is terminal — no downstream consumer may reinterpret it as a clean result.
- `score` always matches the fixed GAME-013 table for the given `outcome`; an incompatible GAME-014 termination contract is rejected before play and can never emit a guessed result.

## Failure/error behavior

An incomplete audit (peer disconnected before Final Reveal) never produces a `verified: true` result; the sub-game closes as a reliability failure (C04's concern) with no settlement, distinct from a `TAMPERED` outcome.

## Version / compatibility

Additive-only.

## Governing requirement IDs

REPORT-005 (consumer-side: reports only settle a verified result); GAME-013.

## Police/Thief identity requirement

**Yes** — both sides must derive the identical verdict independently for REPORT-009's mutual-agreement requirement to be checkable at all.
