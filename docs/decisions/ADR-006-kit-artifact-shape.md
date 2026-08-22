---
artifact: adr
id: ADR-006
status: proposed
date: 2026-08-22
owners:
  - orchestrator
related_requirements:
  - FR-RP-01
  - FR-RP-02
  - FR-RP-03
  - REPORT-005
  - REPORT-006
  - REPORT-007
  - REPORT-008
  - REPORT-009
related_tasks:
  - T033
  - T046
supersedes: []
---

# ADR-006 — Kit-shaped artifact shape for replay port (D-01)

## Context

The replay port workstream requires a verifiable, partner-interoperable artifact shape for offline replay verification. The reference kit's artifact writer states in its docstring that its names and the shared `game_uid` "follow the book's App. F table 20 exactly". The App. F table 20 names are `log_*/config_*/declaration_*/result_*` with a shared `game_uid` across the four documents.

The PRD PRD_replay_port.md §10 lists open decisions D-01…D-08. D-01 concerns artifact shape. The operational convention recorded in ADR-004 allows building interop artifacts behind an adapter while official templates remain open.

The internal reporting contract T032 provides an internal schema only; official template adoption is blocked on INPUT-001/T016.

## Decision

Adopt the App. F table 20 names with nested `{payload, nonce, commit}` records and one shared `game_uid`, written as canonical bytes.

Specifically:
- Log document: `log_{game_id}_g{NN}.json` with schema_version, game_id, game_uid, links, interop, summary, records[], opponent_records[], mutual_agreement.
- Config document: `config_{game_id}_g{NN}.json` with schema_version, game_id, game_uid, links, interop, sub_game_number, config_name, terms, config_sha256.
- Declaration and result documents follow the same naming and interop labeling.
- Each record is `{payload, nonce, commit}` where payload is canonical JSON with step/sender/intent/state/move/hint for reveal records and step/sender/intent for commit records.
- All four documents share the same `game_uid`.
- Files are written as canonical JSON bytes with trailing newline.

This shape is implemented behind `KitInteropAdapter` as an interop artifact, not as the official `SubGameLog`.

## Alternatives considered

- Wait for official templates (T016) and emit no interop artifacts now. Rejected: blocks headless replay verification and rule-20 evidence.
- Emit internal shape only. Rejected: partner verifier expects App. F shape.
- Invent a placeholder field to fill missing data. Rejected: would change payload hash and break re-hash.

## Consequences

Positive:
- Logs are verifiable by partner tooling and by the headless verifier.
- Harness stays reference-identical to the kit.
- Enables FR-RP-01..03, REPORT-005..009 via interop.

Negative:
- Two artifact families coexist until official templates arrive.
- Terms bytes appear in both internal and interop files.

Interoperability:
- The interop artifact is explicitly labeled `INTERNAL/INTEROP — NOT OFFICIAL` per D-02.

Security/verification:
- Re-hash exactness is preserved; no placeholder fields are invented.
- Foreign-log degradation policy D-03 applies.

## Validation

- `tests/unit/transport/test_replay_records.py` round-trip identity and re-hash exactness.
- `tests/unit/transport/test_replay_verify.py` TC-RP-01..10.
- `tests/unit/reporting/test_kit_artifacts.py` doc shapes and canonical bytes.
- `tests/integration/test_replayable_bundle.py` honest end-to-end bundle verification.
- `diff -rq` common/ across repos remains 0.

## Approval

- Decision owner: orchestrator
- Approved by:
- Approval date:
