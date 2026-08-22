---
id: T036
status: blocked
priority: P0
task_type: component
component: C03
optional: false
implements:
  - ARCH-002
  - ARCH-003
  - NET-001
context_files:
  - docs/decisions/ADR-005-shared-protocol-layer-placement.md
  - common/transport/negotiate.py
  - common/transport/audit.py
read_set:
  - src/police_peer/wire/__init__.py
depends_on:
  - T035
  - T009
gates:
  - id: PLANNING-GRAPH-T009-T030
    kind: overlap
    scope: common/transport/series.py
    blocks: start
  - id: THIEF-T036-BYTE-PARITY
    kind: cross-repo
    scope: common/transport/negotiate.py+audit.py
    blocks: start
parallel_safe: false
claimed_by:
claim_expires_at:
write_set:
  - common/transport/negotiate.py
  - common/transport/audit.py
  - src/police_peer/wire/__init__.py
  - tests/unit/transport/
  - tests/unit/wire/
risk: medium
---

# T036 — Wave W2: Validated Wire, Role-Correct Sequencing, Capture Ack, Audit Idempotency (police_repo)

Mirrors `thief_repo`'s `T036` shared-file patch byte-for-byte (per `ADR-005`, `ADR-007`), then
adapts `src/police_peer/wire/__init__.py` to the same sequencing/capture-ack/idempotency
contract. Does not independently redesign the shared files.

## Expected outcome

Identical contract to `thief_repo`'s `T036`: validated wire boundary, role-correct
sequencing (Police responds within a sub-game after Thief's half-turn, per `ADR-001`),
first-class capture acknowledgement, and idempotent audit replay.

## Constraints

- Do not merge until `thief_repo`'s `T036` has landed and its exact shared-file content is
  available to diff against.
- Do not widen into `T035` or `T019` scope.

## Acceptance criteria

- [ ] `common/transport/negotiate.py` and `common/transport/audit.py` are byte-identical to the versions landed by `thief_repo`'s `T036`.
- [ ] Out-of-order/replayed message rejection, capture-acknowledgement, and audit-idempotency behave identically to `thief_repo`'s equivalent tests, adapted to Police-side role sequencing.

## Verification

- `uv run pytest tests/unit/transport tests/unit/wire`
- `uv run python scripts/check_planning_graph.py`
- `diff` the two shared files against the named thief_repo source SHA — must be empty.

## Handoff contract

Report files changed, tests executed, exact results, source SHA matched, decisions, deviations, blockers.

## Result and evidence
