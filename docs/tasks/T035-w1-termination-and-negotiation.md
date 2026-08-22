---
id: T035
status: blocked
priority: P0
task_type: component
component: C01
optional: false
implements:
  - ARCH-002
  - ARCH-003
context_files:
  - docs/spec/OPEN_QUESTIONS.md
  - docs/decisions/ADR-005-shared-protocol-layer-placement.md
  - common/transport/subgame.py
read_set:
  - src/police_peer/wire/__init__.py
depends_on:
  - T004
  - T010
gates:
  - id: PLANNING-GRAPH-T009-T030
    kind: overlap
    scope: common/transport/series.py
    blocks: start
  - id: THIEF-T035-BYTE-PARITY
    kind: cross-repo
    scope: common/transport/subgame.py
    blocks: start
  - id: OPEN-011
    kind: decision
    scope: termination
    blocks: criterion
parallel_safe: false
claimed_by:
claim_expires_at:
write_set:
  - common/transport/subgame.py
  - src/police_peer/wire/__init__.py
  - tests/unit/wire/
  - tests/integration/test_series_loopback.py
risk: medium
---

# T035 — Wave W1: Termination and Per-Subgame Negotiation (police_repo)

## Purpose

Mirror `thief_repo`'s `T035` shared-file patch to `common/transport/subgame.py` byte-for-byte
(per `ADR-005`, `ADR-007`), then adapt `police_repo`'s own wire glue to the same termination
convention. `thief_repo` is the source-of-truth repository for the shared file in this wave;
this task does **not** independently redesign `common/transport/subgame.py`.

## Expected outcome

Identical to `thief_repo`'s `T035`: `OPEN-011`-conformant termination refusal behavior, and
per-subgame (not per-series) negotiation re-validation, using `src/police_peer/wire/__init__.py`
as the Police-side wire adapter equivalent of `thief_repo`'s `wire/session.py`.

## Constraints

- Do not merge until `thief_repo`'s `T035` has landed and its exact `common/transport/subgame.py`
  content is available to diff against — this task's gate `THIEF-T035-BYTE-PARITY` blocks start.
- `OPEN-011` stays officially open; record only the operational convention.
- Do not touch `common/transport/negotiate.py` or `common/transport/audit.py` — `T036` (W2) scope.

## Acceptance criteria

- [ ] `common/transport/subgame.py` in `police_repo` is byte-identical to the version landed by `thief_repo`'s `T035`.
- [ ] `max_moves != survival_threshold` at sub-game start is refused with a typed error, not a silent clamp.
- [ ] Move-cap exhaustion below `survival_threshold` produces an unresolved/refused result.
- [ ] Per-subgame negotiation re-runs and is covered by a test that changes terms between sub-games within one series.

## Verification

- `uv run pytest tests/unit/wire tests/integration/test_series_loopback.py`
- `uv run python scripts/check_planning_graph.py`
- `diff common/transport/subgame.py <(git show <thief_repo T035 sha>:common/transport/subgame.py)` — must be empty.

## Handoff contract

Report files changed, tests executed, exact results, the thief_repo source SHA matched, decisions, deviations, blockers.

## Result and evidence
