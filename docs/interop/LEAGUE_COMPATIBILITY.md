---
artifact: interop-policy
id: LEAGUE-COMPATIBILITY
status: draft
owner: orchestrator
updated: 2026-08-16
---

# League Compatibility Policy

## Purpose

State how this project's peers interoperate at the protocol boundary when the official
specification leaves an implementation detail unresolved. The project team has approved one
operational interoperability profile (`ADR-004` in each role repository) so the first working
implementation has a concrete, testable wire and scent contract instead of an unresolved
ambiguity. Compatibility is never the project's purpose, and no external artifact defines any
part of this project's internal architecture.

## Authority

1. The official project specification and the official software-quality guide outrank every
   operational convention in this policy.
2. Non-authoritative supporting evidence never overrides the official book, and never silently
   resolves an OPEN item. Where such evidence exists, it is tracked in
   `requirements/EVIDENCE_REGISTER.md` with its license terms and authority label.
3. This policy defines **no part of this project's internal architecture**. C01–C06 and their
   contracts are derived from the canonical requirements.

## Compatibility surface

Limited to the interoperability boundary: canonical bytes (`planning/contracts/CT-04-canonical-bytes.md`), the peer wire envelope (`planning/contracts/CT-03-peer-wire.md`), `game_uid`/declaration shape, and report-consensus signatures — the same surface OPEN-001/OPEN-007/OPEN-008/OPEN-009 already govern. An adapter, not internal redesign, is the only acceptable integration shape.

## Adapters, not lock-in

Non-authoritative conformance vectors or fixtures, where used, live behind the same adapter boundary the official contract would occupy once resolved — as a conformance vector for an adopted profile (M-01 §B, CT-03) or as a differential test case (per the compatibility decision matrices still in M-05 and M-07). Any officially-compliant peer must remain a fully valid opponent regardless of which profile it implements, and no adopted profile is written into the domain core.

## Adopted profile (human-approved, operational convention)

The project team has approved one default interoperability profile, recorded in `ADR-004` in each role repository (`docs/decisions/`) and detailed in `planning/contracts/CT-03-peer-wire.md` and `planning/mechanisms/M-01-scent-model.md`:

| Axis | Adopted value |
|---|---|
| `wire_shape` | `reference-v3` |
| `scent_model` | `subtractive_chebyshev_v1` (default) |
| `scent_model` | `multiplicative_book_v1` (additionally supported) |
| `info_mode` | `belief` |
| `smell_binding` | current/unbound; `commit_grid_v1` is **not adopted** |

Adopting this profile is an engineering decision. It does not close OPEN-009, OPEN-007, or OPEN-001, and does not override the book.

## Governance and maturity

Any non-authoritative supporting material is registered in `requirements/EVIDENCE_REGISTER.md` with its own authority label before a task may treat it as more than a differential test case. Nothing without explicit team approval is on the critical path.

## What is prohibited

- Strategy design is project-native; any non-authoritative material supplies interoperability wiring only.
- No non-approved candidate extension is adopted without explicit team approval.
- Third-party material stays a read-only compatibility reference, outside the adapter boundary, and is never vendored into this project's source.
- Applicable license notices must accompany any third-party code or vectors actually incorporated into this project; `requirements/EVIDENCE_REGISTER.md` records the terms.

## Task ownership

Each task proves the compatibility surface **it actually owns**, at the point it builds that surface. T022 is the later full-system gate, not the first place a vector is ever run.

| Task | Interop responsibility |
|---|---|
| T005 | Owns the two registered scent profiles and their conformance vectors; proves both models and the selected-model declaration/lock during T005 itself |
| T008 | Owns canonical bytes and commit-reveal; proves its own byte-level primitives against the relevant golden vectors during T008 itself |
| T009 | Owns the `reference-v3` local peer adapter: tool/argument surface, turn-message keys, locked-model declaration, turn order — all provable locally |
| T012 | Delivery-safety behavior any interoperable peer would also need |
| T016, T018 | Schema adoption and reporting reconciliation touchpoints |
| T019, T020 | League/series and pairing conformance touchpoints |
| **T022** | **Full interoperability/recovery gate** — full two-process series, fault injection, and external friendly proof before counted play. It re-runs the surfaces above end-to-end; it is not where they are first proven |

## Opponent independence

Every C03/C06 contract is written from the canonical requirements first; adherence to this profile is additive. Nothing in this policy or in T022's scope requires the counted opponent to implement any particular external codebase.
