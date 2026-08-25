---
artifact: contract
id: CT-01
status: draft
owner_component: C01
shared: true
updated: 2026-08-15
---

# CT-01 — Game State & Legal Action

## Owner

C01 (Game Core & Configuration).

## Consumers

C02 (Perception & Strategy) — reads the legal-action set and current state to decide; C04 (Runtime & Reliability) — sequences turns against this state; C05 (Observability & Replay) — projects this state's local-truth view.

## Input

An action request: `{action: MOVE(dir) | STAY | BARRIER(target_cell), actor: own_role}`.

## Output

Either an updated game state (own position, own barrier set, board, step count) with no leakage
of the opponent's true position, or a typed rejection with no state change; a compatible
terminal condition yields a `{outcome, score}` verdict per GAME-013, while incompatible
GAME-014 values are rejected before play.

## Externally visible invariants

- An illegal action never mutates state (GAME-004…008, GAME-012).
- A placed barrier is irreversible and impassable to both agents until game end (GAME-007).
- The domain boundary never computes or returns the opponent's true position (hidden-position constraint, derived from STRAT-001/OBS-002/GAME-009…011).
- All numeric parameters come from the validated `config/game.json`/`.toml` (CFG-001…008), never a hardcoded literal outside the CFG-006 Fixed set.

## Failure/error behavior

Rejection carries the specific violated rule (e.g. "diagonal move rejected — GAME-005"), never a generic error. An incompatible GAME-014 termination contract raises a typed refusal before play.

## Version / compatibility

Additive-only: new optional fields may be added to the state/action shape without breaking a consumer that ignores unknown fields. A breaking change (removing or repurposing a field) requires an ADR and a coordinated update across every consumer.

## Governing requirement IDs

GAME-001…014, ARCH-001…003, CFG-001…008.

## Police/Thief identity requirement

**Yes** — byte-identical rule evaluation is required; a divergence here makes the two peers' games disagree about legality or score, which is a correctness defect, not a stylistic one.
