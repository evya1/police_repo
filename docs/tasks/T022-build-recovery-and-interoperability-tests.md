---
id: T022
status: blocked
priority: P1
task_type: integration
component: system
optional: false
implements:
  - NET-001
  - NET-005
  - SEC-002
  - SEC-005
  - REPORT-009
context_files:
  - docs/PRD.md
  - docs/PLAN.md
  - docs/interop/LEAGUE_COMPATIBILITY.md
  - docs/decisions/ADR-004-operational-interoperability-profile.md
  - docs/decisions/ADR-011-league-kit-interoperability-boundary.md
read_set: []
depends_on:
  - T011
  - T012
  - T018
  - T019
  - T052
  - T053
  - T054
gates:
  - id: G-LIVE
    kind: input_gate
    scope: live_interop
    blocks: integration
parallel_safe: true
claimed_by:
claim_expires_at:
write_set:
  - tests/integration/test_full_series.py
  - tests/integration/test_recovery_matrix.py
  - tests/contract/test_cross_peer_vectors.py
  - tests/integration/test_league_kit_live.py
  - tests/contract/test_league_kit_vectors.py
  - docs/interop/LEAGUE_COMPATIBILITY.md
risk: high
---

# T022 — Build Recovery And Interoperability Tests

## Expected outcome

Two-process contract and fault-injection suites prove lifecycle recovery, deterministic audit closure, and report agreement across clean independent instances.

## Requirements implemented

- `NET-001`
- `NET-005`
- `SEC-002`
- `SEC-005`
- `REPORT-009`

## Relevant context

Tests cover derived failure controls without elevating their internal message shapes to official requirements. This task owns the full interoperability/recovery gate named `live_interop`, defined in the project-level integration plan (not duplicated in this repository). `docs/interop/LEAGUE_COMPATIBILITY.md` (local copy) governs the league-kit conformance work this task performs.

**This task is not the first place low-level vectors run.** Under `ADR-004`, each owning task proves its own compatibility surface at the point it builds it: T005 proves both scent profiles and the selected-model declaration against their conformance vectors, T008 proves its canonical-byte and commit primitives against the published golden vectors, and T009 proves the `reference-v3` tool/argument/turn-order contract locally. This task re-runs those surfaces as a whole system under fault injection and across a full series. A finding here that a single primitive is wrong means an earlier task's suite was incomplete, and the fix belongs there.

## Gates

- `G-LIVE` (`input_gate`, `blocks: integration`) — the task completes locally; it cannot pass the `live_interop` integration gate in the project-level integration plan until this resolves.

## Constraints

- Do not edit the canonical PRD.
- Do not silently redefine the repository PLAN or task dependencies.
- Do not widen scope or treat a derived design decision as a source requirement.
- Edit only the declared write set; request an orchestrator-approved change before crossing it.
- Escalate requirement conflicts, missing official inputs, and newly discovered work.

## Acceptance criteria

- [ ] Two fresh processes complete a six-sub-game series with no shared memory.
- [ ] Loss, duplicate, reorder, stale step, disconnect, slow response, crash, and restart cases have deterministic outcomes.
- [ ] Audit binds reveals to stored live commitments and rejects fabricated, missing, impossible, or mutated histories.
- [ ] Cross-peer serialization fixtures include Unicode, floats, compact/spaced separators, Nonce placement, and signature-insertion edge cases; production expectations follow only the approved contract.
- [ ] Compatibility failures for report-layout, scent-profile, tie-profile, and draft-versus-send mismatches are detected before counted play.
- [ ] A full series is played end to end against an external uncounted peer — a sparring or friendly run, not self-play — and the mutual audit settles clean in both role directions before any counted play is scheduled.
- [ ] Both independently derived result artifacts compare consistently before any send call.

### Kit interoperability amendment (ADR-011, added 2026-08-23)

`T022` additionally owns the external `copthief-league-protocol` kit gates, pinned at commit
`ad6557626587e09146af4283a5e808e7001343c5` (MIT). This amendment does not replace the criteria
above; it adds the kit as one required external interoperability target under the same
`G-LIVE` gate. Depends on `T052` (protocol/lifecycle compatibility) and `T053` (kit artifact
projection) landing first.

- [ ] K0: `python verify_vectors.py` at the pinned commit reproduces the reviewed baseline
      (125 checks, 15 fixtures, all pass) — recorded as evidence, not assumed.
- [ ] K1: local contract conformance — every CORE vector and every PROMOTED surface used by
      `reference-v3` is ported or invoked; the two PROPOSED families (`game_uid` declaration,
      `smell_binding`) are exercised but not made mandatory unless both peers declare
      comparable values; the MCP surface (`negotiate`/`receive_turn`/`submit_audit` required,
      `receive_control` optional) is proven to enqueue and return without running game logic
      inline on the handler thread.
- [ ] K2: four live six-sub-game runs through the public composition root (`create_peer` /
      `PeerFacade.run`, never a hand-rolled diagnostic loop) — this repo as police vs. kit as
      thief, this repo as thief vs. kit as police, and (via the sibling repo) the same two
      directions for Thief — each as two independent OS processes in separate Python
      environments (kit: `fastmcp>=2,<3`; this project: FastMCP 3.x), both exiting `0`, all six
      sub-games settling with clean mutual audits, one stable `game_id`/`game_uid`, matching
      outcome/score per sub-game, step counts differing by at most one, no deadlock, no leaked
      child process.
- [ ] K3: `python tools/check_artifacts.py <dir>` and `python -m sparring.cli replay <dir>
      --expect-clean` pass on an honest T053 projection of a six-game run (all six logs
      verified, zero tampered, exit `0`); negative controls (byte mutation without
      re-digesting, content mutation with a regenerated digest, a missing member, a changed
      `game_uid`, a dropped sub-game result row, conflicting peer result artifacts) each
      produce the correct distinct non-zero attribution — never described as external
      authenticity.
- [ ] K4: the required live-kit gate runs template/no-provider mode; deterministic fake-provider
      tests (Hebrew text, an emoji, explicit non-zero token usage) prove movement, barrier
      placement, capture truth, verdict, score, `game_id`, and `game_uid` stay identical for a
      fixed seed across provider absent/success/timeout/exception/malformed-reply/rejected-
      wording; only hint bytes, fallback reason, provider metadata, and honestly sealed token
      accounting may differ; fallback never erases already-consumed tokens.
- [ ] `G-LIVE` resolves only for the pinned, uncounted sparring target once K0–K4 pass — this
      never resolves counted-play or official-template (`official_schema`) gates, which remain
      separately gated on league scheduling and INPUT-001/T016 respectively.

## Verification

- `uv run pytest tests/integration tests/contract`
- `uv run ruff check tests/integration tests/contract`
- `python verify_vectors.py` (run inside the pinned kit checkout, K0)
- `python tools/check_artifacts.py <artifact-dir>` (K3, inside the pinned kit checkout)
- `python -m sparring.cli replay <artifact-dir> --expect-clean` (K3, inside the pinned kit checkout)
- `uv run pytest tests/integration/test_league_kit_live.py tests/contract/test_league_kit_vectors.py`

## Implementation plan

To be completed immediately before execution.

## Handoff contract

Report files changed, tests executed, exact test results, decisions made, deviations, blockers, and newly discovered work. Include command output or artifact paths sufficient for the orchestrator to validate every acceptance criterion.

## Result and evidence
