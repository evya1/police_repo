---
artifact: component-plan
id: PLAN-C05-POLICE
component: C05
status: draft — shallow, internal design deferred
derived_from: PRD-C05
owner: orchestrator
updated: 2026-08-15
---

# C05 — Observability & Replay (Police PLAN)

**This PLAN is deliberately shallow.** Internal design is authored by T014/T015 when claimed, per `planning/COMPONENTS.md`'s authoring-depth rule.

## Purpose (repeated from the component PRD for orientation)

`src/police_peer/ui/live.py` and `ui/view_model.py` — the local-truth Live GUI and belief heatmap. `src/police_peer/ui/replay.py` — the immutable, per-step-verifying Replay Viewer.

## What is fixed now

- Owns OBS-001…006, QR-017.
- Consumes CT-05 (observability event projection) exclusively — never a second, independently-derived state source.
- Replay calls C03's audit algorithm (M-05) for per-step verification; it does not reimplement hashing.

## What T014/T015 will author here when claimed

View-model structure, GUI toolkit selection (gated by PLANQ-007), input-lock implementation detail, Replay navigation state machine, real-screenshot evidence-capture workflow.

## Known risks (fixed now, detail deferred)

Any code path that reads objective opponent state instead of CT-05's redacted projection is a direct OBS-002 violation — the projection boundary, not GUI-layer discipline alone, is what makes this structurally hard to get wrong.
