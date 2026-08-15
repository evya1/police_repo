---
artifact: component-prd
id: PRD-C04
component: C04
status: draft
shared: true
owner: orchestrator
updated: 2026-08-15
---

# C04 — Runtime & Reliability

## Purpose

Own the single gateway that sequences the other components through an explicit game-lifecycle state machine, and the deadline/retry/watchdog behavior that keeps the peer from hanging or losing evidence when the network or the sibling peer misbehaves.

## Requirements owned (primary)

ARCH-004, ARCH-005, ARCH-006, ARCH-008 (the Orchestrator gateway, explicit state machine, rejection of illegal transitions, independent Watchdog); NET-005 (bounded deadline/retry/technical-loss behavior — the normative core is "rather than waiting indefinitely," a reliability behavior, not a wire-format concern). 5 requirements total.

## Requirements consumed / affected

- NET-001…004 (C03): the envelope this component retries or times out is C03's; C04 does not redefine the wire format, only the waiting/retry policy around it.
- CFG-007, CFG-008 (C01): `retry_backoff_sec`, `max_retries`, `response_timeout_sec`, `watchdog_timeout_sec` are consumed here as the operative defaults; C01 owns their definition and validation.
- OBS-001…004 (C05): the GUI projects this component's lifecycle state and turn-lock signal.
- REPORT-005 (C06): a report only settles a sub-game this component has actually driven to a terminal state.

## Observable behavior

- The Orchestrator is the single gateway to the peer's subsystems and coordinates them without embedding decision logic or low-level communication logic (ARCH-004).
- The game lifecycle is governed by an explicit state machine that rejects every transition not present in the legal transition map (ARCH-005, ARCH-006).
- An independent Watchdog detects stalls or crashes, persists state for recovery, and performs controlled shutdown (ARCH-008).
- Every MCP request carries a timestamp and expiry deadline; after expiry the system performs a controlled retry or declares technical loss rather than waiting indefinitely (NET-005).

## Inputs

Legal-action decisions from C02 (via CT-02); verified frames/results from C03 (via CT-03/CT-06); configuration defaults from C01 (CFG-007, CFG-008).

## Outputs

Lifecycle-state transitions consumed as observability events by C05 (via `planning/contracts/CT-05-event-projection.md`); a verified sub-game result consumed by C06 (via `planning/contracts/CT-06-verified-result.md`); watchdog checkpoints.

## Invariants

- No transition outside the implemented legal transition map is ever applied.
- A terminal-failure state never silently repairs itself; recovery re-enters a legal state or ends the sub-game.

## Constraints

- Move heuristics or protocol encoding are never embedded in the Orchestrator (ARCH-004's "must not own" boundary).

## Failure cases

Request expiry, session termination, process stall/crash — see the failure/retry/recovery table this component's PLAN will define once claimed (T010, T011).

## Edge cases

To be enumerated by T010/T011 against the state-model transition table; this PRD intentionally does not pre-specify every transition to avoid micro-planning stale detail before the owning task claims it.

## Acceptance scenarios

- [ ] Every transition not in the legal map is rejected with no side effect. {#transition_rejection}
- [ ] A request past its deadline triggers bounded retry then technical loss, never an indefinite wait. {#deadline_bounded}
- [ ] Watchdog persists a safe checkpoint and performs controlled shutdown on simulated stall. {#watchdog_recovery}

## Relevant contracts

`planning/contracts/CT-02-strategy-decision.md` (consumer); `planning/contracts/CT-03-peer-wire.md` (consumer); `planning/contracts/CT-05-event-projection.md` (owner); `planning/contracts/CT-06-verified-result.md` (co-owner with C03).

## Relevant OPEN/input gates

None block local work. This component's tasks (T010, T011) have no `depends_on` edge on T001 and no `gates:` entry with `blocks: start`.

## Definition of Done

Internal design deferred to the component PLAN, authored when T010/T011 are claimed (see `planning/COMPONENTS.md`'s authoring-depth note). This PRD's three acceptance scenarios and the ARCH-004…008/NET-005 ownership are the fixed contract that PLAN must satisfy.
