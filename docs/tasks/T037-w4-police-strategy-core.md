---
id: T037
status: blocked
priority: P0
task_type: component
component: C02
optional: false
implements:
  - ARCH-007
  - STRAT-007
  - STRAT-008
  - STRAT-009
context_files:
  - docs/mechanisms/M-03-police-strategy.md
  - docs/decisions/ADR-006-strategy-heuristic-priorities.md
  - docs/PRD_police_strategy.md
  - docs/PLAN_police_strategy.md
  - docs/TODO_police_strategy.md
read_set:
  - src/police_peer/strategy/police.py
  - src/police_peer/strategy/barriers.py
  - src/police_peer/strategy/hints.py
  - src/police_peer/strategy/decision.py
depends_on:
  - T007
  - T006
gates:
  - id: PLANQ-008
    kind: decision
    scope: heuristics
    blocks: criterion
parallel_safe: true
claimed_by:
claim_expires_at:
write_set:
  - src/police_peer/strategy/
  - tests/unit/strategy/
  - tests/property/strategy/
risk: medium
---

# T037 — Wave W4a: Police Strategy Core (police_repo)

## Scope note

Unlike the Thief side, Police strategy core work is **not** fully landed on this
governance session's working branch (`claude/github-pr-34-refactor-wjynny`, at `5f7c3bf`).
That commit already contains `src/police_peer/strategy/{police.py,barriers.py,hints.py,
decision.py}` (Phase A/B of the `police-strategy` TODO), but the GitHub PR #34 head has
since force-moved to `c335818` with further Phase D work — this task's job is to reconcile
whichever branch state is authoritative at claim time against `ADR-006`'s Police ordering,
not to assume either branch is complete.

## Expected outcome

- A deterministic Police policy ranks only legal actions (movement or barrier placement)
  from role-local state and belief, per `ADR-006`'s Police ordering: legal action/barrier
  only → quota → no self-blocking route → process capture responses before moving → then
  belief-peak pursuit and threshold-gated barrier placement.
- Hint generation stays isolated from movement selection (existing `AGENTS.md` /
  `T007-implement-role-strategy.md` constraint).
- The two `ADR-006` negative controls (always-STAY opponent, disconnected-belief) are
  seeded and reproducible.

## Constraints

- Do not edit the canonical PRD/PLAN.
- Reconcile against the current `police-strategy` branch state before writing new code —
  do not duplicate Phase A/B/D work that already exists there; port forward what is sound,
  flag what conflicts with `ADR-006`'s approved ordering as a finding.
- Barrier placement must never self-block Police's own future legal movement (hard
  constraint #3) — this must be an explicit, tested guard, not an emergent property.

## Acceptance criteria

- [ ] Barrier/movement ranking follows the exact `ADR-006` Police ordering; deviations are documented findings, not silent choices.
- [ ] Barrier placement never removes Police's own only legal route (self-blocking guard, tested).
- [ ] Capture responses are processed before the next movement action is chosen (ordering test).
- [ ] Always-STAY and disconnected-belief negative controls exist and pass with documented expected outcomes.
- [ ] `T007`'s `heuristics`-scoped acceptance criterion can be closed on this evidence.

## Verification

- `uv run pytest tests/unit/strategy tests/property/strategy`
- `uv run ruff check src/police_peer/strategy tests/unit/strategy`

## Handoff contract

Report files changed, tests executed, exact results, reconciliation findings against the
`police-strategy` branch state, decisions, deviations, blockers, newly discovered work.

## Result and evidence
