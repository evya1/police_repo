---
artifact: component-prd
id: PRD-C05
component: C05
status: draft
shared: true
owner: orchestrator
updated: 2026-08-15
---

# C05 — Observability & Replay

## Purpose

Own the local-truth Live GUI that lets a role watch its own play without leaking the opponent's true state, and the immutable Replay Viewer that lets anyone re-verify a completed match step by step.

## Requirements owned (primary)

OBS-001…006 (dedicated local-truth GUI, no bird's-eye/objective board, belief heatmap, turn-state/input-lock display, Replay navigation, per-step verification with TAMPERED display and disqualification); QR-017 (UI status visibility/error prevention/recovery/accessibility with real screenshots). 7 requirements total.

## Requirements consumed / affected

- OBS-007, SUB-012 (system): honest-evidence submission rules govern how this component's screenshots may be used in README/submission material; this component only produces the evidence.
- SEC-005, SEC-006 (C03): Replay's per-step verification calls C03's audit algorithm; it does not reimplement hashing.
- STRAT-006 (C02): the belief heatmap renders C02's belief output verbatim.

## Observable behavior

- Each role runs a dedicated GUI displaying its local truth only (OBS-001); it never displays a bird's-eye or complete objective board including the opponent's true position (OBS-002).
- The GUI displays a dynamic heatmap of this role's belief about the opponent's location only (OBS-003), and displays turn state with input locked after Commit until the next turn (OBS-004).
- A Replay Viewer loads a final log and allows forward/backward navigation (OBS-005); it verifies every step against its commitment, displays Verified OK on success and red TAMPERED on failure, and disqualifies the game after one failure (OBS-006).

## Inputs

Lifecycle/turn-state events from C04 (via CT-05); belief snapshots from C02; a finalized, audited log from C03.

## Outputs

A rendered Live GUI view; a rendered Replay view; captured real screenshots consumed by the System-scope README/evidence tasks (T023).

## Invariants

- Never renders the opponent's objective position, under any view mode.
- Replay verification result is deterministic given the same log — it never "fixes" a TAMPERED verdict.

## Constraints

- No second rules engine inside the GUI/Replay layer; both call C01/C03's existing verification, they do not reimplement it.

## Failure cases

To be enumerated by T014/T015's acceptance criteria when claimed.

## Edge cases

To be enumerated by T014/T015 against the view-model test strategy; intentionally deferred to avoid pre-specifying UI detail before the owning task claims it.

## Acceptance scenarios

- [ ] The Live GUI never displays the opponent's true position under any tested view state. {#no_leak}
- [ ] Replay navigates forward and backward through a full log and verifies every step. {#replay_navigation}
- [ ] A tampered log step displays red TAMPERED and disqualifies the game. {#replay_tamper}

## Relevant contracts

`planning/contracts/CT-05-event-projection.md` (consumer).

## Relevant OPEN/input gates

None block local work. `PLANQ-007` (GUI toolkit choice) has `blocks: start` on T014 only, not on this PRD's content.

## Definition of Done

Internal design deferred to the component PLAN, authored when T014/T015 are claimed. This PRD's three acceptance scenarios and the OBS-001…006/QR-017 ownership are the fixed contract that PLAN must satisfy.
