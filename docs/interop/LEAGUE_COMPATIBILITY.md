---
artifact: interop-policy
id: LEAGUE-COMPATIBILITY
status: draft
owner: orchestrator
updated: 2026-08-15
---

# League Compatibility Policy

## Purpose

State how this project relates to the `copthief-league-protocol` interoperability kit (`EVID-001` in `requirements/EVIDENCE_REGISTER.md`), a commonly-used third-party kit many participants may adopt. Compatibility with it is a useful, minimum-effort option — never the project's primary purpose or its architecture.

## Authority

1. The kit is a **compatibility target, not an authority**. The official project specification and the official software-quality guide outrank it in every conflict.
2. The kit's own documentation records that its reference behavior and the official book sometimes differ (`WARNINGS.md` in the kit, per read-only inspection of `sources.zip:repo2/`). Compatibility evidence from the kit **never** overrides the official book, and never silently resolves an OPEN item.
3. The kit defines **no part of this project's internal architecture**. C01–C06 and their contracts are derived from the canonical requirements, not from the kit's structure.

## Compatibility surface

Limited to the interoperability boundary: canonical bytes (`planning/contracts/CT-04-canonical-bytes.md`), the peer wire envelope (`planning/contracts/CT-03-peer-wire.md`), `game_uid`/declaration shape, and report-consensus signatures — the same surface OPEN-001/OPEN-007/OPEN-008/OPEN-009 already govern. An adapter, not internal redesign, is the only acceptable integration shape.

## Adapters, not lock-in

Where a kit vector or fixture is used as a differential test case (per the compatibility decision matrices in M-01, M-05, M-07), it lives behind the same adapter boundary the official contract would occupy once resolved. A non-kit, officially-compliant peer must remain a fully valid opponent — the kit is optional, not a dependency.

## Governance and maturity

The kit's own `GOVERNANCE.md` defines four maturity tiers with an explicit promotion bar. Registrations under the kit are therefore **not uniformly mature**, and this project does not adopt a kit profile or proposed extension merely because it exists — each requires explicit team approval before any task treats it as more than a differential test case.

## What is prohibited

- No strategy is copied from another team via the kit or otherwise.
- No kit-defined optional/proposed extension is adopted without explicit team approval.
- The kit's reference implementation is never vendored into this project (`EVID-001` stays a read-only reference in `EVIDENCE_REGISTER.md`).
- License notices are preserved if any kit code or vector is ever actually copied (MIT, Team ImreEyal and contributors) — this migration copies none.

## Task ownership

| Task | Interop responsibility |
|---|---|
| T008, T009 | Canonical-bytes and wire adapters — the seam where a kit-compatible mode, if ever adopted, would attach |
| T012 | Delivery-safety behavior a kit-compatible peer would also need |
| T016, T018 | Schema adoption and reporting reconciliation touchpoints |
| T019, T020 | League/series and pairing conformance touchpoints |
| **T022** | **Full interoperability/conformance gate** — owns any actual conformance-vector testing, kit or otherwise |

## Non-kit peers

Every C03/C06 contract is written from the canonical requirements first; a kit-compatible adapter is additive. Nothing in this policy or in T022's scope requires the counted opponent to use the kit.
