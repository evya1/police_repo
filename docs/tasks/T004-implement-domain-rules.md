---
id: T004
status: blocked
priority: P0
task_type: component
component: C01
optional: false
implements:
  - GAME-001
  - GAME-002
  - GAME-003
  - GAME-004
  - GAME-005
  - GAME-006
  - GAME-007
  - GAME-008
  - GAME-009
  - GAME-010
  - GAME-011
  - GAME-012
  - GAME-013
  - GAME-014
context_files:
  - docs/components/C01-game-core/PRD.md
  - docs/components/C01-game-core/PLAN.md
read_set: []
depends_on:
  - T003
gates:
  - id: OPEN-011
    kind: open
    scope: terminal_map
    blocks: criterion
parallel_safe: true
claimed_by:
claim_expires_at:
write_set:
  - src/police_peer/domain/board.py
  - src/police_peer/domain/rules.py
  - src/police_peer/domain/scoring.py
  - tests/unit/domain/test_board.py
  - tests/unit/domain/test_rules.py
  - tests/unit/domain/test_scoring.py
risk: high
---

# T004 — Implement Domain Rules

## Expected outcome

Pure deterministic board, movement, barrier, capture, terminal-condition, and scoring logic implements the binding rules and rejects illegal actions.

## Requirements implemented

- `GAME-001`
- `GAME-002`
- `GAME-003`
- `GAME-004`
- `GAME-005`
- `GAME-006`
- `GAME-007`
- `GAME-008`
- `GAME-009`
- `GAME-010`
- `GAME-011`
- `GAME-012`
- `GAME-013`
- `GAME-014`

## Relevant context

Rules must operate only on role-local truth. The fixed scoring table and configured Minimum/Negotiated bounds are inputs, not hard-coded alternative values.

## Gates

- `OPEN-011` (`open`, `blocks: criterion`) — the task may be claimed and implemented now; only the acceptance criterion scoped `terminal_map` waits.

## Constraints

- Do not edit the canonical PRD.
- Do not silently redefine the repository PLAN or task dependencies.
- Do not widen scope or treat a derived design decision as a source requirement.
- Edit only the declared write set; request an orchestrator-approved change before crossing it.
- Escalate requirement conflicts, missing official inputs, and newly discovered work.

## Acceptance criteria

- [ ] Property and example tests cover boundaries, cardinal moves, STAY, and diagonal rejection.
- [ ] Barrier placement, persistence, quota, collision, and trapped-Thief capture follow the official rules.
- [ ] A Police capture claim names its current post-move cell; arbitrary-cell claims are rejected, Thief responses are truth-checked, and all fixed scores are deterministic.
- [ ] Move-cap and survival termination use the signed configuration; a move-cap-vs-survival-threshold divergence refuses to score rather than guessing a precedence. `{#terminal_map}`
- [ ] No network, GUI, LLM, clock, or filesystem dependency enters domain logic.

## Verification

- `uv run pytest tests/unit/domain/test_board.py tests/unit/domain/test_rules.py tests/unit/domain/test_scoring.py`
- `uv run ruff check src/police_peer/domain tests/unit/domain`

## Non-functional budgets

- Purity: no network, GUI, LLM, clock, or filesystem import in `src/police_peer/domain/`; enforced by import audit alongside `ruff check`.
- Determinism: identical `(config, action sequence)` input MUST produce byte-identical legal-move ordering, terminal outcome, and scores across repeated runs and fresh process instances.
- Legal-move enumeration MUST use one fixed, documented order so a seeded policy built on `T007` is reproducible.
- Complexity: every domain operation is bounded by the board size; a full `max_moves`-step two-agent simulation completes in well under one second.
- The domain object carries no mutable module-level/global state; every transition acts on an explicit, passed-in sub-game object.

## Hidden-position constraints

- A role's domain state holds only its own position; it never computes or stores the opponent's true position (`STRAT-001`, `OBS-002`).
- Barriers are public once declared and are held identically by both sides' domain state (`GAME-012`).
- A terminal condition that depends on the opponent's position is decided by the side entitled to know it at that moment: the Thief's own domain state detects a barrier placed on its cell and its own entrapment; the Police side emits the Capture Claim naming its own post-move cell, and the Thief's domain state answers from its own local position (`GAME-009`–`GAME-011`; the truthfulness obligation and its detection are `SEC-007`, owned by `T008`, not restated here).

## Domain test vectors

Uses the canonical Appendix F key names only (`grid_size`, `max_barriers`, `max_moves`, `survival_threshold` — never a synonym). `GAME-014`'s move-cap-versus-survival-threshold relationship is blocked by `OPEN-011`; the vectors below test each threshold independently and do not assume an ordering between them.

| Requirement | Test | Input | Expected |
|---|---|---|---|
| GAME-001 | board geometry | 7×7: cells `(3,3)`, `(0,0)`, `(6,6)` in bounds; `(7,0)`, `(-1,3)` out | correct verdicts |
| GAME-003 | defaults | default config, 7×7 | Thief start `(3,3)` (center), Police start `(0,0)` (corner) |
| GAME-003 | axis agreement | both peers configured with the same `axis_origin_corner`/`axis_start_index` | identical cell interpretation |
| GAME-004 | corner move set | from `(0,0)` | legal set exactly `{S, E, STAY}` in fixed order |
| GAME-004 | center move set | from `(3,3)` on empty 7×7 | `{N, S, E, W, STAY}` in fixed order |
| GAME-005 | diagonal rejection | diagonal action from any cell | rejected |
| GAME-004/GAME-005 | off-board rejection | `N` from `(0,0)` | rejected |
| GAME-007 | barrier rejection | move into a barrier cell | rejected |
| — (determinism) | reproducibility | legal-move enumeration from the same `(cell, barriers)` in two fresh instances | identical lists, same order |
| GAME-006 | placement rules | Police STAYs, places at an orthogonal neighbor | accepted; a Police move on the same turn is rejected |
| GAME-006 | placement rules | Police at `(3,3)` targets `(3,5)` (two steps away) | rejected |
| GAME-006 | placement rules | Thief attempts any placement | rejected |
| GAME-007 | permanence | move into a previously placed barrier cell, any later turn | rejected; no removal API exists |
| GAME-008 | quota | 14th placement vs. 15th placement (quota 14) | accepted / rejected |
| GAME-008 | opponent quota | 15th declared opponent barrier absorbed against the same signed quota | rejected |
| GAME-012 | declaration | declared barrier in bounds, not already blocked | appended to local barrier set |
| GAME-012 | declaration | declared barrier out of bounds | rejected |
| GAME-009 | capture by claim | Police moves onto Thief cell, claims its own post-move cell | capture; scores 20/5 |
| GAME-009 | invalid claim | claim names a cell that is not Police's post-move cell | claim rejected |
| GAME-010 | blocking placement | barrier dropped on Thief's occupied cell | capture, detected by the Thief's own domain state |
| GAME-011 | entrapment | Thief in a corner with both adjacent cells barred | capture |
| GAME-011 | not trapped | Thief in a corner with one adjacent cell free | not captured |
| GAME-014 | survival threshold reached | step counter reaches the configured `survival_threshold` with no capture | SURVIVAL; scores 5/10 |
| GAME-014 | move cap reached | step counter reaches the configured `max_moves` with no capture and below `survival_threshold` | outcome blocked by OPEN-011; test asserts the domain refuses to guess rather than silently scoring |
| GAME-013 | score table | every `(outcome, role)` pair defined so far | matches GAME-013 exactly |
| GAME-013 | sanction vs. tie | a technical-loss outcome (e.g. from `T008`/`T011`) scores 0/0 | domain never reports a 0/0 outcome as a tie |

## Implementation plan

To be completed immediately before execution.

## Handoff contract

Report files changed, tests executed, exact test results, decisions made, deviations, blockers, and newly discovered work. Include command output or artifact paths sufficient for the orchestrator to validate every acceptance criterion.

## Result and evidence
