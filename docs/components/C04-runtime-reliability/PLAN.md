---
artifact: component-plan
id: PLAN-C04-POLICE
component: C04
status: draft — shallow, internal design deferred
derived_from: PRD-C04
owner: orchestrator
updated: 2026-08-15
---

# C04 — Runtime & Reliability (Police PLAN)

**This PLAN is deliberately shallow.** Per `planning/COMPONENTS.md`'s authoring-depth rule, internal design for C04 is authored by T010/T011 when claimed, not pre-specified here — micro-planning stale future detail before the owning task starts is prohibited by `docs/spec/PRD_PLAN_TODO_AGENT_WORKFLOW.md` §10.

## Purpose (repeated from the component PRD for orientation)

The single gateway (`src/police_peer/orchestration/`) that sequences C01/C02/C03 through an explicit lifecycle state machine, plus the deadline/retry/watchdog layer (`src/police_peer/reliability/`) that prevents indefinite waiting.

## What is fixed now

- Owns ARCH-004…006, ARCH-008, NET-005 (see `docs/components/C04-runtime-reliability/PRD.md`).
- Consumes CT-01 (game state), CT-02 (strategy decisions), CT-03 (peer wire); produces CT-05 (observability events) and co-owns CT-06 (verified result) with C03.
- The state model table (BOOTSTRAP → NEGOTIATING → READY → COMPUTING → COMMITTED → ACKNOWLEDGED → REVEALING → WAITING → AUDITING → REPORTING → COMPLETE/TAMPERED/FAILED) is the binding transition map; T010 implements the exact event vocabulary against it.

## What T010/T011 will author here when claimed

Exact module layout inside `orchestration/` and `reliability/`; the retry-journal/idempotency-key design; the watchdog checkpoint format; the failure/retry/recovery table for each of NET-005's failure modes (request expiry, session termination, process stall/crash); local test strategy.

## Known risks (fixed now, detail deferred)

Retry duplicates or forked state; watchdog false-positive stalls under legitimate long-running verification steps.
