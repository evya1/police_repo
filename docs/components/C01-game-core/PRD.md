---
artifact: component-prd
id: PRD-C01
component: C01
status: draft
shared: true
owner: orchestrator
updated: 2026-08-15
---

# C01 — Game Core & Configuration

## Purpose

Own the pure, deterministic rules of the game (board, movement, barriers, capture, scoring) and the shared/private configuration boundary that carries the negotiated game terms both peers must apply identically. This is the one component neither peer can get wrong without breaking interoperability, because both sides execute the same rules against different local state.

## Requirements owned (primary)

ARCH-001, ARCH-002, ARCH-003, ARCH-009 (process isolation and the module boundary that carries it); GAME-001…014 (board, movement, barriers, capture, scoring, termination); CFG-001…010 (shared/private configuration contract, precedence, Appendix F status validation, per-game configuration lifecycle). 28 requirements total.

## Requirements consumed / affected

- STRAT-001, STRAT-004 (C02): strategy reads legal-action output from this component but never computes it.
- NET-001 (C03): the transport layer carries this component's `config/game.json` unmodified.
- OBS-001…004 (C05): the GUI projects this component's local state, never invents it.
- REPORT-006…008 (C06): report artifacts embed the locked configuration and per-sub-game outcomes this component produces.
- CFG-007, CFG-008 are consumed by C04 (retry/timeout defaults) without C04 owning their definition.
- CFG-009, CFG-010 are consumed by C06 (Git commit id in reports) without C06 owning the configuration-lifecycle rule.

## Observable behavior

- Given a `config/game.json` shared contract and a `config/game.toml` private file, the component validates every Appendix F Fixed/Minimum/Negotiated value and rejects a mismatch before play (CFG-001…008).
- Given a legal action (move N/S/E/W/STAY, or a barrier declaration), the component updates only the acting side's own position/barrier state and rejects an illegal one with no state change (GAME-004…008, GAME-012).
- Given a terminal condition — Police lands on the Thief cell with a valid Capture Claim, a barrier lands on the Thief's cell, the Thief has no legal move, or a fixed step count is reached — the component emits the correct outcome and score from GAME-009…014, or refuses to score and surfaces `gates: [{id: OPEN-011, ...}]` when the move-cap/survival-threshold ordering is genuinely ambiguous.
- Given a new game, the component enforces that configuration changes only under recorded opponent agreement and that a per-game configuration file with a unique name is committed (CFG-009, CFG-010).

## Inputs

Shared `config/game.json` (Appendix F terms), private `config/game.toml`, an incoming legal-action request from Strategy (C02, via `docs/contracts/CT-01-game-state.md`), a step count.

## Outputs

A validated game state; a legal/illegal action verdict with no side effects on illegal; a terminal-outcome verdict with score when applicable; a validated configuration snapshot consumed by every other component through CT-01.

## Invariants

- **Hidden-position constraint** (derived from STRAT-001, OBS-002, GAME-009…011): the domain boundary holds only this role's own position and never computes or stores the opponent's true position. Barriers are public once declared and held identically by both sides' domain state. A terminal condition depending on the opponent's position is decided only by the side entitled to know it — the Thief's own domain state detects a barrier on its cell and its own entrapment; the Police side emits the Capture Claim while the Thief's domain state answers from its own local position.
- Shared JSON always takes precedence over private TOML on a shared key; TOML cannot weaken a signed condition (CFG-003).
- A placed barrier is irreversible and impassable to both agents until the game ends (GAME-007).
- Diagonal movement is always rejected (GAME-005).

## Constraints

- No network, GUI, clock, or credential dependency in this component (see `planning/contracts/CT-01-game-state.md`'s "must not own" column).
- All Appendix F values come from configuration, never a hardcoded literal, except the CFG-006 Fixed set which may be asserted directly.

## Failure cases

- Config validation failure (mismatched Fixed value, Minimum value below threshold, missing Negotiated agreement): refuse before Step 0, name the exact differing field.
- Illegal action: reject with no state change; caller receives a typed rejection, not a silent no-op.
- Move-cap-versus-survival-threshold divergence (OPEN-011): refuse to score rather than guess a precedence.

## Edge cases

- A barrier declared on the acting Police's own current cell (permitted; GAME-006).
- A move that would leave the board (rejected; GAME-004).
- Simultaneous capture-eligible and barrier-entrapment conditions in the same turn (GAME-009 vs. GAME-011 — test vector required, not a documentation gap).
- A negotiated value with no agreement recorded (falls back to the printed default; CFG-005/CFG-008).

## Acceptance scenarios

- [ ] Board/movement/barrier legality holds for the full domain test-vector table (see the component PLAN's test strategy). {#board_vectors}
- [ ] Capture, barrier-entrapment, and no-legal-move terminal conditions each produce the correct GAME-013 score. {#terminal_vectors}
- [ ] A move-cap-vs-survival-threshold divergence is refused rather than scored. {#cap_refusal}
- [ ] Every Appendix F Fixed/Minimum/Negotiated status validates against the CFG-006/007/008 defaults with no error on the expected-valid vector set. {#config_validation}

## Relevant contracts

`planning/contracts/CT-01-game-state.md` (owner) — the public game-state and legal-action surface every other component consumes.

## Relevant OPEN/input gates

- OPEN-011 — terminal-outcome map; `blocks: criterion` on `{#cap_refusal}`. The binding minimum of 35 for both `max_moves` and `survival_threshold`, and the GAME-013 score table, are unaffected.
- OPEN-005 — reclassified `implementation_status: RESOLVED_LOCALLY`; `blocks: criterion` only on labeling a proposed negotiated change to a Minimum parameter, never on `{#config_validation}`.
- OPEN-001 (via ADR-001) — the negotiated nested shape for `config/game.json` is our own engineering choice pending official confirmation; it does not block this component's implementation.

## Definition of Done

All acceptance scenarios pass with recorded test evidence; the domain module never imports network, GUI, or Gmail code; `check_planning_graph.py` shows CFG-*/GAME-*/ARCH-001…003,009 owned only here; T003/T004/T028/T029 acceptance criteria (which this PRD's scenarios mirror) are independently verifiable from this PRD and `planning/contracts/CT-01-game-state.md` alone.
