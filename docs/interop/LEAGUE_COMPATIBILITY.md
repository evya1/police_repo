---
artifact: interop-policy
id: LEAGUE-COMPATIBILITY
status: active
owner: orchestrator
updated: 2026-08-16
---

# League Interoperability Policy

## Purpose

State how this project reaches byte-level and turn-level agreement with an independently written opponent, and where that agreement is allowed to touch the codebase.

## Authority order

1. The official project specification and the official software-quality guide govern in every conflict.
2. The canonical requirements (`requirements/CANONICAL_REQUIREMENTS.md`) govern below them.
3. The operational conventions recorded in `docs/decisions/ADR-004-operational-interoperability-profile.md` and the contracts it references govern only where the two levels above leave a detail undefined.

No interoperability convention overrides an official requirement, and none closes an `OPEN-*` item. Where a convention and the source diverge, the divergence is stated plainly in the owning mechanism or contract document rather than hidden.

## Interoperability surface

Interoperability is confined to a named boundary:

- canonical bytes and the commitment preimage — `planning/contracts/CT-04-canonical-bytes.md`;
- the peer wire envelope, tool surface, and turn-message keys — `planning/contracts/CT-03-peer-wire.md`;
- the scent model and its declared lock — `planning/mechanisms/M-01-scent-model.md`;
- the `game_uid`/declaration shape and report-consensus signatures — `planning/mechanisms/M-07-report-reconciliation.md`.

Everything else — component boundaries C01–C06, domain rules, belief, strategy, orchestration, observability — follows from the canonical requirements and is not part of the interoperability surface.

## Adapters, not lock-in

Every interoperability convention is implemented behind an adapter. The domain core and the strategy modules never branch on a profile value, never import a transport module, and never read a wire key. An officially compliant peer that declares a different profile remains a fully valid opponent: the adapter changes, not the core.

## Selected profile

The selected operational conventions are recorded once, in `docs/decisions/ADR-004-operational-interoperability-profile.md`:

| Family | Selected value |
|---|---|
| `wire_shape` | `reference-v3` |
| `scent_model` | `subtractive_chebyshev_v1` (default) |
| `scent_model` | `multiplicative_book_v1` (additionally supported) |
| `info_mode` | `belief` |
| `smell_binding` | current/unbound; `commit_grid_v1` not adopted |
| turn order | the thief takes the first game turn |

These are exact protocol literals, compared across peers as strings. They are never renamed, re-cased, or translated.

## Declaration and refusal

Each family's active value is declared at negotiate time as a SHA-256 hash over a pinned parameter document. Refusal fires only when both peers declare a family and the declared hashes disagree; omission by either side is never refusal. A refused start produces a diagnostic naming the disagreeing family and leaves no partial game state.

## Verification ownership

Each task proves the part of the surface it owns, at the point it builds that surface.

| Task | Interoperability responsibility |
|---|---|
| T005 | Both scent profiles, their vectors, and the model declaration/lock |
| T008 | Canonical bytes, the commitment preimage, and their golden vectors |
| T009 | The `reference-v3` adapter: tool/argument surface, turn-message keys, profile declarations, turn order |
| T012 | Inbound delivery safety on the same envelope |
| T016, T018 | Artifact schema adoption and reporting reconciliation |
| T019, T020 | Series and pairing conformance |
| **T022** | **Full interoperability/recovery gate** — a complete two-process series, fault injection, and an uncounted external run. It re-runs the surfaces above end to end; it is not where any of them is first proven |

## Third-party material

No external code, fixture, or vector is incorporated into either role repository without orchestrator approval, a recorded license review, and preservation of every legally required copyright, license, and NOTICE text. Where such material is incorporated, its required notices ship with the repository that distributes it. Removing or omitting a required notice is prohibited regardless of how small the incorporated material is.

## Prohibited

- Treating any non-official profile, vector, or peer behavior as authority for an `OPEN-*` answer.
- Writing a profile value into the domain core, the strategy modules, or the scoring table.
- Adopting an extension that changes a commit preimage without an explicit team decision recorded in an ADR.
- Requiring a counted opponent to use any particular profile; a mutually agreed alternative is negotiated, not assumed.
