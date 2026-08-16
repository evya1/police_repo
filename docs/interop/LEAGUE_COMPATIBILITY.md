---
artifact: interop-policy
id: LEAGUE-COMPATIBILITY
status: draft
owner: orchestrator
updated: 2026-08-16
---

# League Compatibility Policy

## Purpose

State how this project relates to the `copthief-league-protocol` interoperability kit (`EVID-001` and `EVID-003` in `requirements/EVIDENCE_REGISTER.md`), a commonly-used third-party kit many participants may adopt. The project team has approved it as our **first integration target**: the first working implementation should interoperate directly with the current kit's runnable sparring peer. That is a decision about integration sequence, not about authority or architecture — compatibility is never the project's purpose, and the kit defines no part of our internal design.

## Authority

1. The kit is a **compatibility target, not an authority**. The official project specification and the official software-quality guide outrank it in every conflict.
2. The kit's own documentation records that its reference behavior and the official book sometimes differ (`WARNINGS.md` in the kit, per read-only inspection of `sources.zip:repo2/`). Compatibility evidence from the kit **never** overrides the official book, and never silently resolves an OPEN item.
3. The kit defines **no part of this project's internal architecture**. C01–C06 and their contracts are derived from the canonical requirements, not from the kit's structure.

## Compatibility surface

Limited to the interoperability boundary: canonical bytes (`planning/contracts/CT-04-canonical-bytes.md`), the peer wire envelope (`planning/contracts/CT-03-peer-wire.md`), `game_uid`/declaration shape, and report-consensus signatures — the same surface OPEN-001/OPEN-007/OPEN-008/OPEN-009 already govern. An adapter, not internal redesign, is the only acceptable integration shape.

## Adapters, not lock-in

Where a kit vector or fixture is used — as a conformance vector for an adopted profile (M-01 §B, CT-03) or as a differential test case (per the compatibility decision matrices still in M-05 and M-07) — it lives behind the same adapter boundary the official contract would occupy once resolved. A non-kit, officially-compliant peer must remain a fully valid opponent — the kit is optional, not a dependency, and no adopted profile is written into the domain core.

## Adopted profile (human-approved, non-official)

The project team has approved one default interoperability profile, recorded in the kit-first interoperability ADR in each role repository (`docs/decisions/`) and detailed in `planning/contracts/CT-03-peer-wire.md` and `planning/mechanisms/M-01-scent-model.md`:

| Axis | Adopted value | Upstream maturity at the inspected SHA |
|---|---|---|
| `wire_shape` | `reference-v3` | tool surface `PROMOTED`; locked-model schema `CORE` |
| `scent_model` | `subtractive_chebyshev_v1` (default) | `CORE` |
| `scent_model` | `multiplicative_book_v1` (additionally supported) | `PROMOTED` |
| `info_mode` | `belief` | `PROMOTED` |
| `smell_binding` | current/unbound | the unbound state is registered; `commit_grid_v1` is `PROPOSED` and **not adopted** |

Adopting this profile is an engineering decision. It does not close OPEN-009, OPEN-007, or OPEN-001, does not override the book, and does not promote the kit above the official sources in the authority order above.

## Governance and maturity

The kit's own `GOVERNANCE.md` defines four maturity tiers with an explicit promotion bar. Registrations under the kit are therefore **not uniformly mature**, and this project does not adopt a kit profile or proposed extension merely because it exists — each requires explicit team approval before any task treats it as more than a differential test case. The profile table above records that approval and the maturity tier each adopted item carried when inspected; nothing at `PROPOSED` status is on our critical path.

## What is prohibited

- No strategy is copied from another team via the kit or otherwise.
- No kit-defined optional/proposed extension is adopted without explicit team approval.
- The kit's reference implementation is never vendored into this project (`EVID-001` stays a read-only reference in `EVIDENCE_REGISTER.md`).
- License notices are preserved if any kit code or vector is ever actually copied (MIT, Team ImreEyal and contributors) — this migration copies none.

## Task ownership

Each task proves the compatibility surface **it actually owns**, at the point it builds that surface. T022 is the later full-system gate, not the first place a vector is ever run.

| Task | Interop responsibility |
|---|---|
| T005 | Owns the two registered scent profiles and their conformance vectors; proves both models and the selected-model declaration/lock during T005 itself |
| T008 | Owns canonical bytes and commit-reveal; proves its own byte-level primitives against the relevant golden vectors during T008 itself |
| T009 | Owns the `reference-v3` local peer adapter: tool/argument surface, turn-message keys, locked-model declaration, turn order — all provable locally |
| T012 | Delivery-safety behavior a kit-compatible peer would also need |
| T016, T018 | Schema adoption and reporting reconciliation touchpoints |
| T019, T020 | League/series and pairing conformance touchpoints |
| **T022** | **Full interoperability/recovery gate** — full two-process series, fault injection, and external sparring/friendly proof before counted play. It re-runs the surfaces above end-to-end; it is not where they are first proven |

## Non-kit peers

Every C03/C06 contract is written from the canonical requirements first; a kit-compatible adapter is additive. Nothing in this policy or in T022's scope requires the counted opponent to use the kit.
