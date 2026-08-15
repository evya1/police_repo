---
artifact: mechanism-prd
id: M-03
component: C02
status: draft
shared: false — Police only
owner: orchestrator
updated: 2026-08-15
---

# M-03 — Police Strategy

## Why this mechanism has its own PRD

Pursuit/barrier/capture-claim decision policy is genuinely role-specific and must never leak into the Thief repository (that is what makes it worth separating from the shared C02 component PRD, and worth keeping out of the bundle entirely — this file exists only in `police_repo`).

## Governing requirements

ARCH-007 (strategy is a separate module), STRAT-007 (movement policy freedom — heuristic, custom algorithm, or RL, none required), STRAT-008 (verbal-text boundary), STRAT-009 (hint negotiability).

## Specified behavior (binding)

- Movement policy may use heuristics, a custom algorithm, or reinforcement learning; none is required (STRAT-007).
- The policy selects only from C01's legal-action set (via CT-01); it never invents an action.
- Barrier declarations are always truthful and open (GAME-012, owned by C01, consumed here as a hard constraint on the policy's candidate actions).
- A Capture Claim, once the Police peer is positioned to make one, must be truthful (SEC-007, owned by C03, consumed here).

## Police-specific decision shape (derived design, not an official requirement)

Pursuit prioritizes closing distance toward the peak of the belief distribution (M-02's output) while respecting the barrier quota (GAME-008) and preferring barrier placement when it can convert a probable Thief position into a forced capture. This is this project's own engineering choice — PLANQ-008 records the approved heuristic priorities and seeded scenarios once the team decides them; it is not itself a canonical requirement.

## Verbal-hint boundary

Hint generation (template or optional provider, STRAT-008) is isolated from movement selection by the same module boundary ARCH-007 requires. A hint may be truthful or deceptive (STRAT-009); it never determines the selected action.

## Acceptance scenarios

- [ ] The pursuit policy always selects from C01's legal-action set. {#pursuit_legality}
- [ ] Barrier placement never occurs without an open declaration in the same turn. {#barrier_honesty}
- [ ] Hint generation cannot influence the already-selected movement action. {#hint_isolation}

## Owning task

T007 (`ARCH-007, STRAT-007…009`), depends on T004, T006.
