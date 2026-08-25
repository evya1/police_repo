---
id: T035
status: done
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
gates: []
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

Identical to `thief_repo`'s `T035`: production termination refusal behavior and
per-subgame (not per-series) negotiation re-validation, using `src/police_peer/wire/__init__.py`
as the Police-side wire adapter equivalent of `thief_repo`'s `wire/session.py`.

## Constraints

- Police/Thief `common/transport/subgame.py` behavior remains byte-identical.
- Incompatible termination values are rejected before play.
- Do not touch `common/transport/negotiate.py` or `common/transport/audit.py` — `T036` (W2) scope.

## Acceptance criteria

- [x] `common/transport/subgame.py` behavior is byte-identical across both repositories.
- [x] `max_moves != survival_threshold` at sub-game start is refused with a typed error, not a silent clamp.
- [x] Incompatible termination values cannot produce a guessed score.
- [x] Per-subgame negotiation re-runs and is covered by a test that changes terms between subgames.

## Verification

- `uv run pytest tests/unit/wire tests/integration/test_series_loopback.py`
- `uv run python scripts/check_planning_graph.py`
- `diff common/transport/subgame.py <(git show <thief_repo T035 sha>:common/transport/subgame.py)` — must be empty.

## Handoff contract

Report files changed, tests executed, exact results, the thief_repo source SHA matched, decisions, deviations, blockers.

## Result and evidence

Complete. The full unit/integration suites and cross-repository parity gate verify the shared
termination and per-subgame negotiation behavior.
