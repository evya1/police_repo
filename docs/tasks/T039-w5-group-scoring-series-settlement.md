---
id: T039
status: blocked
priority: P1
task_type: component
component: C01
optional: false
implements:
  - ARCH-002
context_files:
  - docs/PRD.md
  - docs/spec/OPEN_QUESTIONS.md
read_set:
  - src/police_peer/league/series.py
  - src/police_peer/league/scoring.py
depends_on:
  - T019
  - T035
  - T036
gates:
  - id: PLANNING-GRAPH-T009-T030
    kind: overlap
    scope: common/transport/series.py
    blocks: start
  - id: THIEF-T039-BYTE-PARITY
    kind: cross-repo
    scope: common/transport/series.py
    blocks: start
parallel_safe: false
claimed_by:
claim_expires_at:
write_set:
  - src/police_peer/league/series.py
  - src/police_peer/league/scoring.py
  - common/transport/series.py
  - tests/unit/league/
risk: medium
---

# T039 — Wave W5: Group-Based Scoring and Series Settlement (police_repo)

Mirrors `thief_repo`'s `T039` shared-file patch to `common/transport/series.py`
byte-for-byte, then applies the equivalent group/pool settlement logic to
`src/police_peer/league/`. Same `OPEN-011` refusal discipline applies.

## Expected outcome

Identical settlement contract to `thief_repo`'s `T039`: correct group/pool aggregation,
and a series containing any unresolved sub-game outcome itself settles as unresolved
rather than guessing.

## Constraints

- Do not merge until `thief_repo`'s `T039` has landed and its exact shared-file content is available to diff against.
- Do not touch reporting artifact schemas (`T016`/`T032` scope).

## Acceptance criteria

- [ ] `common/transport/series.py` is byte-identical to the version landed by `thief_repo`'s `T039`.
- [ ] Group/pool series settlement (3+ participants) and unresolved-sub-game refusal behave identically to `thief_repo`'s equivalent tests.

## Verification

- `uv run pytest tests/unit/league`
- `uv run python scripts/check_planning_graph.py`
- `diff` the shared file against the named thief_repo source SHA — must be empty.

## Handoff contract

Report files changed, tests executed, exact results, source SHA matched, decisions, deviations, blockers.

## Result and evidence
