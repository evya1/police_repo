---
artifact: adr
id: ADR-007
status: proposed
date: 2026-08-22
owners:
  - orchestrator
related_requirements:
  - FR-RP-12
  - OBS-006
  - SEC-005
  - SEC-006
related_tasks:
  - T033
  - T046
  - T016
supersedes: []
---

# ADR-007 — Official-template stance / interop boundary for replay port (D-02)

## Context

The replay port workstream needs a replayable artifact that can be verified offline and exchanged with a partner. Official report artifact schemas are missing; T016 is blocked on INPUT-001. AGENTS.md prohibits relabeling auxiliary artifacts as official.

PLAN_replay_port.md §13/D-02 recommends treating the kit-shaped log as a parallel interop artifact behind `KitInteropAdapter`, explicitly labeled `INTERNAL/INTEROP — NOT OFFICIAL`, and not written into the internal `SubGameLog`.

The reference kit's verifier and artifact writer already assume App. F table 20 names and a shared `game_uid`. The internal reporting contract T032 is INTERNAL only.

## Decision

The kit-shaped log is a parallel interop artifact behind `KitInteropAdapter`. It is not written into the official `SubGameLog`. It is explicitly labeled `INTERNAL/INTEROP — NOT OFFICIAL` in the `interop` block of every document.

The official templates, when they arrive via INPUT-001/T016, will replace the adapter at the same boundary without changing the verifier.

No field is invented to fill missing official data; foreign-log degradation applies.

## Alternatives considered

- Merge interop shape into the official log. Rejected: would violate AGENTS.md prohibition on relabeling auxiliary artifacts as official and would couple to missing official inputs.
- Gate the whole replay port on INPUT-001. Rejected: blocks headless verification and rule-20 evidence, and prevents early integration testing.

## Consequences

Positive:
- Headless replay verification and replayable bundles can proceed now.
- Clear boundary preserves the ability to swap in official templates later.
- Interop artifacts are clearly labeled, avoiding confusion.

Negative:
- Two artifact families coexist until T016 resolves.
- Consumers must be aware of the `interop` label.

Verification:
- All kit-shaped documents include `interop` block with `label`, `boundary`, `authority`.
- Tests assert the label is present and that `verify_dir` ignores internal `SubGameLog` co-location.
- No new third-party dependency; no reference code vendored.

## Validation

- `tests/unit/reporting/test_kit_artifacts.py` asserts `interop` block presence and label.
- `tests/integration/test_replayable_bundle.py` TC-RP-07 co-location test passes.
- `scripts/replay.py` help documents the `replay/` subdirectory requirement.

## Approval

- Decision owner: orchestrator
- Approved by:
- Approval date:
