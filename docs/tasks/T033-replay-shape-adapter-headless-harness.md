---
id: T033
status: not_started
priority: P0
task_type: component
component: C03
optional: false
implements:
  - SEC-005
  - SEC-006
  - OBS-006
context_files:
  - docs/components/C03-peer-protocol-integrity/PRD.md
  - docs/components/C03-peer-protocol-integrity/PLAN.md
  - docs/PRD_replay_port.md
  - docs/PLAN_replay_port.md
read_set: []
depends_on:
  - T008
gates: []
parallel_safe: true
claimed_by:
claim_expires_at:
write_set:
  - common/transport/replay_types.py
  - common/transport/replay_records.py
  - common/transport/replay.py
  - tests/unit/transport/replay_fixtures.py
  - tests/unit/transport/test_replay_records.py
  - tests/unit/transport/test_replay_verify.py
risk: medium
---

# T033 — Strict pure replay core

## Expected outcome

The shared `common/` slice decodes every replay record strictly into frozen types and verifies a
log against its exact configuration as a pure function, with no filesystem access and no shape
guessing. Verdict and coverage are reported honestly and separately.

## Requirements implemented

- `SEC-005`
- `SEC-006` (consumed)
- `OBS-006` (verification engine)

## Relevant context

Implements RP-01, RP-04, RP-05, and RP-11 of `docs/PRD_replay_port.md`. Depends on T008 done.

This task **replaces** the previous first-record/regex shape inference rather than patching around
it. REVIEW_FINDINGS F-01, F-05, F-07, and F-08 are regressions this task must close: `_verify_half`
inspected `from_kit_record(records[0]).get("payload", {})` against a flat record that has no nested
`payload`, so every half was treated as foreign; shape was inferred from one record; and any failed
audit collapsed to `TAMPERED`.

**Trust statement (ARCHITECTURE_AUDIT).** A matching commit proves only that the revealed payload
matches that commit. A party able to rewrite payload, nonce, commit, result, and manifest together
can make an unanchored local bundle internally consistent. Internal consistency is therefore never
reported as historical authenticity.

## Constraints

- Edit only the declared write set.
- `common/` work is written once and synced byte-identical to both repos; no runtime sibling import.
- Pure functions only — no `Path`, no JSON file traversal, no clock, no network in this slice.
- Every code and test file stays below 150 logical lines; shared fixtures live in
  `tests/unit/transport/replay_fixtures.py` so both test modules stay under the cap.
- No DI framework, Repository/Unit of Work, event bus, live external call in tests, or guessed
  official/vendor contract.

## Acceptance criteria

- [ ] `common/transport/replay_types.py` defines frozen `ReplayVerdict`, `VerificationCoverage`,
      `SealedRecord`, `ReplayIssue`, and `ReplayReport` exactly as specified in the shared
      architecture, using `@dataclass(frozen=True, slots=True)` and `StrEnum`.
      `VerificationCoverage` carries one independent boolean per layer: `integrity`,
      `live_binding`, `physics`, `outcome`, `bundle_digests`, `external_authenticity`.
- [ ] `common/transport/replay_records.py` provides strict nested and flat codecs that retain
      canonical payload bytes and validate step, nonce, commitment shape, sequence, and homogeneous
      record shape. Booleans are rejected where integers are required; nonce is non-empty;
      commitment is 64 lowercase hex; steps are unique, ordered, and contiguous from 0.
- [ ] `common/transport/replay.py` provides pure `verify_replay(log_doc, config_doc) -> ReplayReport`
      with exact identity and terms checks, verifying every record through `verify_commit`.
- [ ] Each coverage layer is reported independently and honestly: a supported foreign shape sets
      `integrity` true and `physics`/`live_binding` false rather than collapsing to a single level;
      a mixed shape inside one half is `INVALID`.
- [ ] `external_authenticity` is false whenever no peer receipt or T018-authorized signature has been
      verified, even when every local check passes. `VERIFIED_OK` means "all available checks
      passed", never "historically authentic".
- [ ] Verdicts are distinct: commitment mismatch or withheld committed reveal is `TAMPERED`; physics
      or outcome failure with intact commitments is `ILLEGAL`; malformed syntax, type, or identity is
      `INVALID`; absent required evidence is `INCOMPLETE`.
- [ ] The first-record heuristic and the regex shape inference are deleted, not bypassed.
- [ ] Tests cover empty, malformed, and mixed shape; duplicate, skipped, negative, and out-of-order
      steps; wrong config and wrong UID; both halves; semantic payload mutation; canonical
      whitespace and key-order behaviour; four physics failures including a role-wrong capture
      claim; foreign degradation; unanchored-recomputed authenticity honesty; and deterministic
      report equality.
- [ ] Ruff clean, line cap ok, and `diff -rq` of `common/` across both repos reports no difference
      after the approved result is ported.

## Verification

- `uv run pytest tests/unit/transport/test_replay_records.py tests/unit/transport/test_replay_verify.py`
- `uv run ruff check common/transport/replay_types.py common/transport/replay_records.py common/transport/replay.py tests/unit/transport`
- `uv run python scripts/check_line_cap.py`
- `diff -rq` common/ across repos

## Result and evidence

(to be filled)
