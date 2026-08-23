---
id: T034
status: not_started
priority: P0
task_type: component
component: C03
optional: false
implements:
  - OBS-006
  - SEC-005
  - SEC-006
context_files:
  - docs/components/C03-peer-protocol-integrity/PRD.md
  - docs/components/C03-peer-protocol-integrity/PLAN.md
  - docs/PRD_replay_port.md
  - docs/PLAN_replay_port.md
read_set: []
depends_on:
  - T008
  - T033
gates: []
parallel_safe: true
claimed_by:
claim_expires_at:
write_set:
  - common/transport/replay_evidence.py
  - common/transport/subgame.py
  - common/transport/series.py
  - tests/unit/transport/test_series_replay_evidence.py
risk: medium
---

# T034 — Immutable per-subgame replay evidence

## Expected outcome

Each played subgame yields a frozen `SubgameReplayEvidence` value carried through `SeriesResult`,
so the runner can publish a replayable bundle. No mutable live record ledger is retained and no
live message, audit, or settlement ordering changes.

## Requirements implemented

- `OBS-006`
- `SEC-005`
- `SEC-006`

## Relevant context

Implements RP-06 of `docs/PRD_replay_port.md`. REVIEW_FINDINGS F-09: live subgame records exist only
in local variables and are discarded when `SeriesRow` is returned, so the runner cannot produce a
replayable bundle at all.

The captured opponent-commitment ledger is what arms offline **live binding** coverage: without it,
an unanchored recomputed bundle could be internally consistent with nothing to compare against.

Evidence capture is an observation of already-created values, not a new state machine.

## Constraints

- Edit only the declared write set.
- `common/` work is written once and synced byte-identical to both repos; no runtime sibling import.
- Preserve live audit ordering, barriers, settlement, and wire messages exactly.
- `SeriesResult` gains a `tuple[SubgameReplayEvidence, ...]` field with an empty default so every
  existing call path stays source-compatible.
- Copy mutable inputs at the boundary; never retain a caller-owned dictionary.
- Every code and test file stays below 150 logical lines.

## Acceptance criteria

- [ ] `common/transport/replay_evidence.py` defines frozen `SubgameReplayEvidence` with the subgame
      index, identity, canonical terms bytes, tuples of `SealedRecord` for both halves, an ordered
      immutable copy of the opponent commitments observed live from `Inbox.played`, result claims,
      and the existing `SeriesRow`.
- [ ] `play_subgame` constructs the evidence at the end from already-existing local values without
      changing message or audit order. The observed-commitment ledger is captured only **after** the
      live audit has consumed the mutable map, so live behaviour is unchanged.
- [ ] `SeriesResult` accumulates six ordered entries as a tuple, defaulting to empty.
- [ ] Tests prove step zero is first, both halves rehash, the observed commitments bind the opponent
      reveals, six ordered entries accumulate, mutating an alias of an input cannot change the sealed
      evidence, and existing series/audit outcomes are identical to before this task.

## Verification

- `uv run pytest tests/unit/transport/test_series_replay_evidence.py tests/unit/transport tests/integration`
- `uv run ruff check common/transport tests/unit/transport`
- `uv run python scripts/check_line_cap.py`
- `diff -rq` common/ across repos

## Result and evidence

(to be filled)
