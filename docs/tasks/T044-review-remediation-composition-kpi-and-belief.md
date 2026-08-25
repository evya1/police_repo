---
id: T044
status: done
priority: P0
task_type: component
component: C02
optional: false
implements:
  - ARCH-002
  - ARCH-003
  - ARCH-007
  - NET-001
  - GAME-009
  - SEC-007
context_files:
  - docs/decisions/ADR-005-shared-protocol-layer-placement.md
  - docs/decisions/ADR-006-strategy-heuristic-priorities.md
  - docs/PLAN_police_strategy.md
  - src/police_peer/runner.py
  - src/police_peer/sdk.py
read_set:
  - src/police_peer/cli.py
  - src/police_peer/belief/grid.py
  - src/police_peer/belief/update.py
depends_on:
  - T038
gates: []
parallel_safe: false
claimed_by: orchestrator
claim_expires_at:
write_set:
  - src/police_peer/runner.py
  - src/police_peer/strategy/base.py
  - src/police_peer/wire/brain.py
  - common/transport/validators.py
  - common/transport/subgame.py
  - common/transport/turnseal.py
  - common/transport/turnfeed.py
  - tests/perf/police_latency_probe.py
  - tests/unit/test_runner_composition.py
  - tests/unit/strategy/
  - tests/unit/transport/
  - tests/unit/wire/
  - tests/property/strategy/
  - tests/integration/test_strategy_selfplay_kpi.py
  - tests/integration/test_strategy_selfplay_kpi_harness.py
risk: high
---

# T044 — Review remediation: production composition, real KPI, belief and hint semantics (police_repo)

Closes the `police_repo` half of the independent review dated 2026-08-22. The shared
`common/transport/{validators,subgame,turnseal}.py` edits are a **byte-for-byte port** from
`thief_repo`'s `T042` (ADR-005 source-of-truth direction); this task verifies parity, it does
not redesign shared behaviour.

Scope is exactly the review's findings. It does **not** change production termination
semantics, group scoring, reporting, GUI, or branch hygiene, and it does **not** change
ADR-007 or `T041`, which stay evaluation-only.

## Findings closed

| Finding | Fix | Evidence |
|---|---|---|
| BLOCKER-1 — `run_one_peer` substituted `BaselineStrategy()` for an omitted strategy, so `create_peer` always took the legacy `StandInEngine` branch and the real `PoliceBrain` was dead code in production | the runner passes `strategy` through unchanged; an explicit `Strategy` still selects the documented legacy path | `tests/unit/test_runner_composition.py`, `tests/unit/wire/test_composition_root.py` |
| HIGH-2 — hostile optional turn data passed validation and could mutate state before failing | byte-for-byte port of the shared validator/preflight; Police `observe_opponent` runs the semantic preflight before belief mutation | `tests/unit/transport/test_turn_validation_general.py`, `tests/unit/wire/test_hostile_turn_atomicity.py` |
| HIGH-3 — the KPI built `BrainDrivenEngine(..., config={})` directly, bypassing the composition root it claimed to measure | the KPI and determinism runs build the Police side with `create_peer` against the shipped `config/game.json` and take engine **and** `PeerConfig` from that facade | `tests/integration/test_strategy_selfplay_kpi_harness.py` |
| MEDIUM-4 — an own barrier kept belief mass and was re-seeded by diffusion | `belief.exclude(cell)` immediately after a **successful** `place_own_barrier` | `tests/unit/wire/test_own_barrier_belief.py` |
| MEDIUM-5 — tests loaded the strategy package through `src.police_peer...` while production imports `police_peer...`, creating two class objects per source file | every test import normalized to the installed package path | `tests/unit/strategy/test_module_identity.py` |
| MEDIUM-6 — TC-P21 measured `where_place_barrier` inside a coverage-instrumented process | the measured loop runs in a clean child process that reports whether a tracer or `coverage` was present | `tests/perf/police_latency_probe.py` |
| MEDIUM-7 — the hint was generated from the pre-move position | `BrainBase.decide` computes the destination of the already-selected action and hints from it; the pinned two-phase order is unchanged | `tests/unit/strategy/test_base.py` |
| Sub-game boundary leak (found by the real two-process run during this wave, not by the review) | byte-for-byte port of `play_subgame`'s boundary reconciliation: the settling peer's owed final STAY (rule 35) is dropped instead of poisoning the next fresh reorder window | `tests/unit/wire/test_hostile_turn_atomicity.py` boundary cases; the cross-repo series below |
| LOW-11 — `RandomThiefEngine` was described as a reference ThiefBrain | renamed `UniformRandomThief` and documented as the seeded random-walk baseline it is | `tests/integration/test_strategy_selfplay_kpi.py` |

## Acceptance criteria

- The CLI → runner → `create_peer` path builds `BrainDrivenEngine` for POLICE by default, and
  the regression lives at the **runner** boundary, not only in an SDK unit test.
- The KPI measures that same composition and holds **>= 60%** capture, with the median-round,
  barrier, determinism and negative-control assertions intact. No threshold lowered, no seed
  count reduced, no negative control deleted.
- Every hostile message is refused as a verdict with zero partial mutation of inbox, applied
  window, board/session and belief.
- An own barrier has probability zero and is absent from `allowed_cells`, and stays so
  through at least six further diffusions; a failed placement leaves belief unchanged.
- `rg -n 'src\.police_peer' tests` returns no matches; production and tests share one class
  object per strategy type.
- TC-P21 <= 10 ms p99 over 10k measured iterations after a 1k warm-up, measured uninstrumented,
  while repository coverage stays enforced at >= 85%.
- `common/` byte-identical to `thief_repo`.

## Result

Evidence SHAs and measured numbers are recorded in `docs/TODO_police_strategy.md`.

## Two-process cross-repo evidence

`police_peer` (from this repository) and `thief_peer` (from `thief_repo`) run as two separate
OS processes over FastMCP on localhost, six sub-games, artifacts written by each side
independently:

| | baseline at the audit anchors | after this wave |
|---|---|---|
| exit codes | 0 / 0 | 0 / 0 |
| `game_uid` match | yes | yes |
| `audit_ok` | 12/12 true | 12/12 true |
| captures | **0** — every sub-game ran to the 35-step ceiling | **3** |
| captures while *this* repository played POLICE | 0 | **3** |
| captures while `thief_repo` played POLICE | 0 | 0 — its SD-T7 stand-in selector never pursues; structural reachability is proved there by a crafted alternating-role test |

The three captures are the end-to-end proof of BLOCKER-1: before the runner fix the CLI
never reached `PoliceBrain`, and the baseline column is what that looked like. The
zero-capture baseline is also why the boundary leak was latent — no sub-game ever ended
early, so no peer ever owed an unread final STAY.

`Session termination failed` (LOW-10) did **not** reproduce on a clean run. It appears only
alongside a crash, and its source is the dependency
`mcp/client/streamable_http.py:593` (`logger.warning`), emitted when the client tears down a
session whose peer process has already exited. No source-owned cause exists and no output is
suppressed.
