---
artifact: component-plan
id: PLAN-C06-POLICE
component: C06
status: draft — shallow, internal design deferred
derived_from: PRD-C06
owner: orchestrator
updated: 2026-08-15
---

# C06 — Reporting & League (Police PLAN)

**This PLAN is deliberately shallow.** Internal design is authored by T016–T020 when claimed, per `planning/COMPONENTS.md`'s authoring-depth rule — C06's schema and sanction detail depends on OPEN-001/004/008, none of which is expected to resolve before C01–C03 complete.

## Purpose (repeated from the component PRD for orientation)

`src/police_peer/reporting/` — official artifact schemas (once OPEN-001 resolves), the reconciliation/settlement algorithm (M-07), and the send-only Gmail pipeline. `src/police_peer/league/` — series/scoring/pairing-eligibility. `src/police_peer/infra/external_api_gatekeeper.py` — the single external-service Gatekeeper (also used by the optional T027 provider).

## What is fixed now

- Owns REPORT-001…013, LEAGUE-001…007, QR-008, QR-018.
- Consumes CT-04 (canonical bytes, non-official draft) and CT-06 (verified sub-game result); never recomputes either.
- M-07's reconciliation algorithm shape (independent derivation → cross-check against peer draft → refuse silent auto-resolution on mismatch) is binding now even though the sanction/tie-aggregation values it plugs into are not.

## What T016–T020 will author here when claimed

Exact artifact-schema module once OPEN-001 resolves; Gatekeeper rate-limit/DOS/backoff/quota implementation; series/scoring module layout; pairing-preflight checklist implementation.

## Known risks (fixed now, detail deferred)

Building a full schema implementation against a guessed OPEN-001 shape (prohibited by NG-004) — mitigated by keeping T016 gated `blocks: start` on OPEN-001/INPUT-001 rather than proceeding speculatively.
