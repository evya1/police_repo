---
id: T005
status: blocked
priority: P0
task_type: component
component: C02
optional: false
implements:
  - STRAT-002
  - STRAT-003
  - STRAT-004
  - STRAT-005
  - CFG-001
  - CFG-004
context_files:
  - docs/components/C02-perception-strategy/PRD.md
  - docs/components/C02-perception-strategy/PLAN.md
  - docs/mechanisms/M-01-scent-model.md
  - docs/decisions/ADR-004-operational-interoperability-profile.md
read_set: []
depends_on:
  - T004
gates:
  - id: OPEN-009
    kind: open
    scope: pairing_preflight
    blocks: integration
parallel_safe: true
claimed_by:
claim_expires_at:
write_set:
  - src/police_peer/scent/model.py
  - src/police_peer/scent/profiles/
  - src/police_peer/scent/lock.py
  - tests/unit/scent/
  - tests/contract/test_scent_agreement.py
risk: high
---

# T005 — Implement Scent Model And Lock

## Expected outcome

Two deterministic 5x5 scent profiles are implemented behind one small common interface, selectable at runtime with `subtractive_chebyshev_v1` as the default, and the selected model is registered, hashed, and declared so a peer mismatch is refused before play.

## Requirements implemented

- `STRAT-002`
- `STRAT-003`
- `STRAT-004`
- `STRAT-005`
- `CFG-001`
- `CFG-004`

## Relevant context

The source fixes center intensity, field size, the update recurrence, decay timing, and anti-forgery behavior. It does not state how repeated emission remains within `[0, 0.9]` — that is `OPEN-009`, and it is still **officially OPEN**.

`ADR-004` supplies what the source does not: two named, separately registered profiles with pinned parameters, and a default. That is a human-approved engineering decision, not an official reading of section 4.3, and nothing in this task may describe it as one. It is nevertheless sufficient to implement, select, declare, and lock a model — so this task no longer waits on an official OPEN-009 answer, and its `{#model_lock}` criterion is no longer gated.

The exact arithmetic of both profiles is stated once, in `docs/mechanisms/M-01-scent-model.md` §B, and must not be re-derived or re-interpreted here. The two profiles genuinely differ in decay form, update order, rounding, upper clamp, and transport; implementing one and adapting it into the other is a defect, not a simplification.

## Gates

- `OPEN-009` (`open`, `blocks: integration`) — the task is implemented and completed locally against the `ADR-004` profile, including model locking. What still waits on an official answer is confirmation, before the `pairing_preflight` gate in `planning/INTEGRATION_PLAN.md`, that the locked profile is acceptable for counted play.

## Constraints

- Do not edit the canonical PRD.
- Do not silently redefine the repository PLAN or task dependencies.
- Do not widen scope or treat a derived design decision as a source requirement.
- Edit only the declared write set; request an orchestrator-approved change before crossing it.
- Escalate requirement conflicts, missing official inputs, and newly discovered work.

## Acceptance criteria

- [ ] A small common scent-model interface exists, and every consumer reaches scent only through it. Adding or changing a profile requires no edit outside the scent module.
- [ ] `subtractive_chebyshev_v1` is implemented exactly as specified in M-01 §B.1: maximum-merge, deposit-then-decay, subtractive decay, rounding to 3 places, lower clamp only, transmitted, receiver-side decay.
- [ ] `multiplicative_book_v1` is implemented exactly as specified in M-01 §B.2: verbatim printed kernel lookup, multiplicative decay, decay-then-deposit, no rounding, `[0, 0.9]` clamp, recomputed rather than transmitted.
- [ ] The active profile is selected by runtime configuration through the existing local private-configuration seam, with no scent code reachable that hardcodes one model.
- [ ] The default selection with no explicit configuration is `subtractive_chebyshev_v1`.
- [ ] The selected model is registered as a pinned parameter document, hashed, and declared for the handshake; the same input document always produces the same hash, and the declaration is carried outside the closed signed-terms set. `{#model_lock}`
- [ ] Vector/golden tests cover **both** registered models against their own conformance vectors, not just the default.
- [ ] Repeated-emission and saturation tests exist for both profiles and assert their genuinely different behavior — no upper clamp under the reference profile, clamping at `0.9` under the book profile.
- [ ] Edge, corner, and out-of-board clipping are deterministic and bounded to the board for both profiles.
- [ ] Emission never occurs at a cell the emitting side does not occupy; each peer exposes only its own field and consumes only the opponent's.
- [ ] A declared-model mismatch refuses start with a diagnostic and no partial game state, at the handshake boundary — never inside the scent module. A peer that declares nothing is not a mismatch and must still play.
- [ ] No strategy, belief, or transport logic exists inside the scent module.

## Verification

- `uv run pytest tests/unit/scent tests/contract/test_scent_agreement.py`
- `uv run ruff check src/police_peer/scent tests/unit/scent tests/contract/test_scent_agreement.py`

## Implementation plan

To be completed immediately before execution.

## Handoff contract

Report files changed, tests executed, exact test results, decisions made, deviations, blockers, and newly discovered work. Include command output or artifact paths sufficient for the orchestrator to validate every acceptance criterion.

## Result and evidence


Not claimed. Integration-baseline state (this branch, `lahav`): no `scent/` module exists under `src/`; T004's `common/domain/` logic is present but T005 has not started against this baseline. Feature-branch state: a scent-model implementation (both registered profiles, the model-lock mechanism, and unit/contract vector tests) exists on the dedicated `feature/issue-8-t005-scent-model-lock` branch. That branch is not merged into `lahav` and is not integrated here. Review state: not reviewed against this task's acceptance criteria. Verification state: not run against this baseline. Integration state: not integrated. Formal task state: not started (this task has not been claimed).
