---
artifact: component-plan
id: PLAN-C01-POLICE
component: C01
status: draft
derived_from: PRD-C01
owner: orchestrator
updated: 2026-08-15
---

# C01 — Game Core & Configuration (Police PLAN)

## Approach summary

A pure, deterministic domain module (`src/police_peer/domain/`) with no network/GUI/clock/credential dependency, plus a configuration boundary (`src/police_peer/config/`) that validates every Appendix F Fixed/Minimum/Negotiated value before Step 0. This is the component T003/T004/T028/T029 already target; this PLAN carries the mechanism-level detail moved out of the old system-wide `docs/PLAN.md`.

## Internal design

- `domain/board.py` — board geometry, position, legality of a raw move (in-bounds, non-diagonal).
- `domain/rules.py` — barrier placement legality, capture/entrapment/no-legal-move terminal detection, the hidden-position constraint (this role's domain state never computes the opponent's true position; the Thief's own domain state answers entrapment/barrier-on-cell questions from its own local position).
- `domain/scoring.py` — the fixed GAME-013 score table and the GAME-014/OPEN-011 refusal path.
- `config/` — Appendix F status validator (Fixed/Minimum/Negotiated), shared-JSON/private-TOML precedence (CFG-003), per-game configuration lifecycle (CFG-009, CFG-010).

## State/responsibility ownership

Domain owns board/rules/scoring state exclusively; config owns the validated parameter snapshot every other component reads through `docs/contracts/CT-01-game-state.md`. Neither owns transport, GUI, or persistence.

## Domain test-vector table

| Case | Expected |
|---|---|
| Move N/S/E/W into an open in-bounds cell | Accepted, position updated |
| Move into a wall/edge | Rejected, no state change |
| Diagonal move | Rejected, no state change (GAME-005) |
| Barrier on own cell or orthogonal neighbor, unblocked | Accepted, movement forfeited this turn |
| Barrier on a non-adjacent cell | Rejected |
| Police lands on Thief cell + valid Capture Claim | CAPTURE, 20/5 |
| Barrier placed on Thief's current cell | CAPTURE, 20/5 |
| Thief has no legal move (all neighbors blocked/off-board) | CAPTURE, 20/5 |
| Step count reaches `survival_threshold` | SURVIVAL, 5/10 |
| Step count reaches `max_moves` without survival/capture, and the two values diverge | Refuse to score (OPEN-011) |

## Turn-adjudication flow

```mermaid
flowchart TD
    A[Turn begins: peer reads contract + local state] --> B{Action type}
    B -->|MOVE N/S/E/W| C{In bounds and cell unblocked?}
    B -->|STAY| D{Police with quota remaining?}
    C -->|no| R[Reject: illegal move, no state change]
    C -->|yes| E[Update own position]
    D -->|yes, declares barrier| F{Target is own cell or orthogonal neighbor, unblocked?}
    D -->|no| G[Remain in place]
    F -->|no| R
    F -->|yes| H[Place barrier and declare it openly]
    E --> I{Terminal condition?}
    G --> I
    H --> I
    I -->|Police on Thief cell plus valid Capture Claim| J["CAPTURE: 20 to Police, 5 to Thief (GAME-013)"]
    I -->|Barrier on Thief cell or Thief has no legal move| J
    I -->|Step count reaches survival_threshold| K["SURVIVAL: 5 to Police, 10 to Thief (GAME-013)"]
    I -->|Step count reaches max_moves without survival or capture| L["Blocked by OPEN-011: refuse to score, do not guess"]
    I -->|none of the above| M[Turn passes to opponent]
```

## Configuration shape (ADR-001)

`config/game.json` uses the negotiated nested-section shape recorded in `docs/decisions/ADR-001-shared-game-contract-shape.md`, authored and validated by T028/T003 respectively — our own engineering choice pending OPEN-001, not an official schema claim.

## Local test strategy

Unit tests per row of the domain test-vector table; property tests for legal-motion invariants and score-derivation determinism; config schema/precedence tests against the CFG-006/007/008 vectors; the OPEN-011 refusal path as an explicit negative test, not a skip.

## Component-level integration

Feeds `docs/contracts/CT-01-game-state.md` to every consumer. T029's local two-agent scripted run is this component's own integration gate (`planning/INTEGRATION_PLAN.md`'s `stage1_gate`) before any other component is treated as able to trust its output.

## Known risks

Byte-level Appendix F drift between the two repos if config validation logic diverges — mitigated by both repos sharing the identical `CANONICAL_REQUIREMENTS.md`/`TRACEABILITY.md` copies and by CT-01 being the only public surface. Overengineering the config layer beyond what CFG-001…010 actually require.
