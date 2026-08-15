---
artifact: component-plan
id: PLAN-C03-POLICE
component: C03
status: draft
derived_from: PRD-C03
owner: orchestrator
updated: 2026-08-15
---

# C03 — Peer Protocol & Integrity (Police PLAN)

## Approach summary

`src/police_peer/transport/` implements symmetric FastMCP server/client adapters and the inbound-delivery-safety hardening (TD-04). `src/police_peer/integrity/` implements the single Commit-Reveal/audit path (M-05) against the internal draft canonicalization (CT-04) until OPEN-007 resolves.

## Internal design

- `transport/mcp_server.py`, `transport/mcp_client.py` — symmetric FastMCP roles (NET-001).
- `transport/contracts.py` — the negotiated, versioned envelope shape (M-06); explicitly labeled non-official pending OPEN-001/OPEN-007.
- `transport/inbox.py` — bounded at-least-once receive safety: absorb exact duplicates, quarantine conflicting duplicates, buffer a configured reorder window, reopen one dropped session within the original deadline (TD-04, derived hardening — not itself an official wire requirement).
- `integrity/commit_reveal.py`, `integrity/audit.py` — the M-05 algorithm: Commit → Acknowledge → Reveal → Final Reveal/Audit, one canonical hashing implementation, TAMPERED with no repair.

## State/responsibility ownership

Transport owns the wire and receive-safety state; integrity owns commitment/audit state and is the only place that computes a canonical hash. Neither owns game decisions.

## Local test strategy

FastMCP contract tests against the local envelope shape; two-process `localhost` smoke test (`tests/integration/test_two_process_smoke.py`); nonce/tamper/replay/physics audit tests; the compatibility decision matrix from M-05/CT-04 exercised as differential tests only, never selecting a production default before OPEN-007.

## Component-level integration

`planning/INTEGRATION_PLAN.md`'s `local_mcp_smoke` gate is this component's first cross-component proof, entirely local. `cross_peer_vectors` stays gated by OPEN-007 until it resolves; `public_endpoint` stays gated by `G-LIVE`.

## Known risks

A local draft canonicalization (CT-04) accidentally treated as production-ready before OPEN-007 resolves — mitigated by the explicit non-official label and the compatibility-matrix pattern. Retry/duplicate logic producing forked state — mitigated by the idempotent receipt journal.
