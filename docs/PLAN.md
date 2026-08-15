---
artifact: plan
id: PLAN-POLICE
status: draft
version: 0.2
derived_from: PRD-FINAL-P2P@0.3
repository_state: greenfield
owner: orchestrator
updated: 2026-08-15
---

# Police System PLAN

**Version 0.2** (bounded-context migration, Issue #3; supersedes v0.1). Mechanism-level detail — the turn-adjudication flowchart, state model, compatibility decision matrices, and per-mechanism technical decisions — moved to the six component PLANs under `docs/components/` and the mechanism PRDs under `docs/mechanisms/`. This System PLAN stays concise: system-wide boundaries, dependency direction, shared contracts, security/config ownership, lifecycle, integration order, and system-level gates.

## Approach summary

Build one autonomous Police peer as six components (`docs/components/README.md`) around a pure local domain core (C01), perception/strategy (C02), peer protocol/integrity (C03), a thin runtime orchestrator (C04), local-truth observability (C05), and reporting/league (C06), connected only through the six boundary contracts (`docs/contracts/`). The repository begins greenfield. Requirement IDs refer to `docs/spec/CANONICAL_REQUIREMENTS.md`; this PLAN selects system-level technical strategy and does not redefine intent.

## Proposed repository structure

The following tree is proposed, not evidence of existing implementation. Directories are created only by the task that owns them.

```text
src/police_peer/
  sdk.py
  config/           # C01
  domain/           # C01
  scent/            # C02
  belief/           # C02
  strategy/         # C02
    providers/          # optional text providers; T027 only
  transport/        # C03
  integrity/        # C03
  orchestration/    # C04
  reliability/       # C04
  infra/            # central external-service Gatekeeper (C06's Gatekeeper user)
  evidence/         # C03 (Step 0, token metering)
  reporting/        # C06
  league/           # C06
  ui/               # C05
tests/
  unit/
  property/
  contract/
  integration/
config/
docs/
  spec/
  inputs/
  components/       # C01…C06 PRD (copy) + PLAN (role-owned)
  mechanisms/        # shared M-01/02/05/06/07 (copy) + M-03 (role-owned)
  contracts/         # CT-01…CT-06 (copy)
  interop/          # LEAGUE_COMPATIBILITY.md (copy)
  tasks/
  decisions/
  changes/
  evidence/
scripts/
notebooks/             # P2 only if T025 is approved
data/derived/          # P2 only if T025 produces real data
```

## Major system boundaries and dependency direction

```text
C01 Game Core & Configuration  ──▶  C02 Perception & Strategy  ──▶  C04 Runtime & Reliability
        │                                                                   │
        └────────────────────▶  C03 Peer Protocol & Integrity  ────────────┤
                                                                             ▼
                                                          C05 Observability & Replay
                                                          C06 Reporting & League
```

C01 has no dependency on any other component. C02 and C03 depend only on C01. C04 depends on C01–C03. C05 and C06 depend only on C04's output (via CT-05/CT-06) — neither reads another component's internals. This is the dependency direction every component PLAN and task's `read_set` must respect.

## Shared contracts

| Contract | Owner | Purpose |
|---|---|---|
| CT-01 game state & legal action | C01 | The one surface every other component reads for board/turn state |
| CT-02 strategy decision | C02 | Selected action + hint, handed to C04 |
| CT-03 peer wire envelope | C03 | FastMCP tool surface and deadline-carrying envelope |
| CT-04 canonical bytes | C03 | Non-official draft commitment preimage, gated by OPEN-007 |
| CT-05 observability event projection | C04 | The only source C05 may read — structurally prevents an OBS-002 leak |
| CT-06 verified sub-game result | C03/C04 | The only settled result C06 may report |

Full contract text: `docs/contracts/CT-0{1..6}-*.md`.

## Local-truth restriction (system-wide)

No component computes, stores, or transmits the opponent's true position except through the narrow, explicitly-permitted exceptions in CT-01's hidden-position constraint (Police's own Capture Claim; the Thief's own entrapment/barrier detection from its own local state). This restriction is enforced at the CT-01/CT-05 boundaries, not only by convention.

## Security boundary

All cryptographic integrity (Commit-Reveal, audit, Nonce custody) is owned exclusively by C03/M-05. No other component computes a hash used for game-legality or audit purposes. All external-service calls (Gmail, any optional language-model provider) pass through one Gatekeeper (`infra/external_api_gatekeeper.py`), owned by C06's requirement set (QR-008) but shared as infrastructure.

## Configuration ownership

C01 owns the entire `config/game.json`/`config/game.toml` validation boundary (CFG-001…010). Every other component consumes the validated snapshot through CT-01; none re-validates or re-interprets a configuration value.

## System lifecycle

Bootstrap → negotiate → play six sub-games → audit → report → close, gated by C04's state machine (detailed in `docs/components/C04-runtime-reliability/PLAN.md` once T010 claims it) and by the human approval gates below.

## Integration order and component gates

See `planning/INTEGRATION_PLAN.md` (bundle-mastered, synchronized reasoning below) for the full named-gate table. In order: component-local gates (per component PLAN's local test strategy) → `local_mcp_smoke`/`stage1_gate` (C01+C03 local proof) → `orchestration_integration` (C04 sequencing) → `cross_peer_vectors` (gated by OPEN-007) → `live_interop` (T022, the full interoperability/conformance gate) → `pairing_preflight`/`report_reconciliation` (final pre-counted-match gates).

## System verification

Full-series verification is the union of every named integration gate passing plus the System-scope tasks: T021 (property/coverage closure), T023 (documentation/evidence), T024 (compliance audit), T026 (release). No task is treated as a trusted integration dependency before its component-local gate passes.

## Recovery

Watchdog-driven checkpoint/recovery is C04's concern (ARCH-008, NET-005); see its component PLAN once T011 claims it. At system level: a recovered peer re-enters the state machine at the last safe checkpoint, never silently repairs a TAMPERED verdict, and never resumes past an expired deadline without the configured retry/technical-loss policy.

## Major architectural decisions (system-scope; component-scope decisions moved to their own PLAN)

### TD-01 — Six components, six contracts, no cross-component internal reads

- **Choice:** every cross-component dependency goes through a named contract (CT-01…CT-06); a component's `read_set` for another component is limited to its published contract, never its internals.
- **Alternatives:** a single monolithic package with implicit coupling; a service-per-file granularity.
- **Reason:** this is the mechanism that makes bounded task context real — a C02 worker builds against CT-01 with a fake Game Core, never reading C01's PLAN.
- **Consequences:** any new cross-component need requires either an existing contract's extension (additive-only) or a new contract, approved by the orchestrator.

### TD-02 — Two-level planning, minimal documentation

- **Choice:** one concise System PRD/PLAN plus six component PRDs and (initially) three substantive component PLANs, deferring C04–C06 internal design to their owning task.
- **Alternatives:** fully detailed PLANs for all six components now; a single flat PLAN as before.
- **Reason:** avoids micro-planning stale detail for components whose specification depends on still-open OPEN items (OPEN-001, 004, 007, 008).
- **Consequences:** C04–C06 PLANs will be revised substantively when T010/T011/T014/T015/T016–T020 are claimed; this is expected, not a defect.

### TD-03 — Project-native contracts with compatibility evidence (retained from v0.1)

- **Choice:** implement from canonical requirements and approved contracts; derive edge-case and compatibility tests from explicit project ambiguities, using the differential-test pattern in each mechanism PRD's compatibility matrix.
- **Reason:** preserves artifact authority and exposes interoperability failures without introducing unsupported schemas or hidden assumptions.

### TD-04 — Minimal Python application shape (retained from v0.1)

- **Choice:** the local, non-standard label `PY-2-minimal` — a maintained Python application with meaningful deterministic rules and external I/O, pure domain core, thin adapters, manual dependency wiring, plain functions for stateless behavior, classes only when they own state/invariants/lifecycle.
- **Reason:** the system has multiple external boundaries and substantial rules, but no demonstrated need for transaction-heavy abstractions or a general extension framework.
- **Consequences:** a DI container, generic Repository/Unit of Work, domain-event bus, or CQRS requires a concrete need and an approved PLAN update or ADR.

### TD-05 — Negotiated nested shape for the shared game contract (retained from v0.1)

- **Choice:** adopt the nested-section `config/game.json` layout recorded in `docs/decisions/ADR-001-shared-game-contract-shape.md`, authored and validated by T028/T003.
- **Reason:** CFG-001/CFG-004 fix which values the contract must carry, not its JSON shape; this is our own negotiable engineering choice, explicitly labeled non-official pending OPEN-001.

## Requirement coverage

Delegated to `docs/spec/TRACEABILITY.md`'s `Primary component` column plus each component PRD's "Requirements owned (primary)" section. This PLAN does not restate the full ARCH/GAME/NET/… coverage table that the previous version carried — it is now traceable per-component instead of duplicated here.

## Parallel execution waves

Unchanged in shape from v0.1, now annotated with owning component (see `docs/TODO.md`'s `Component` column for the authoritative per-task mapping):

| Wave | Tasks | Component(s) | Prerequisites |
|---|---|---|---|
| 0 | T001, T002 | system, foundation | none |
| 1 | T003 | C01 | T002 |
| 2 | T004, T008, T009, T017, T028 | C01, C03, C03, C06, C01 | T003 (T009 also T003 only — see TODO) |
| 2-opt | T029 | C01 | T004, T028 |
| 3 | T005, T016 | C02, C06 | T004 (T016 gated by G-OFFICIAL) |
| 4 | T006, T010 | C02, C04 | T005; T010 also T004/T008/T009 |
| 5 | T007, T011, T012, T013, T014 | C02, C04, C03, C03, C05 | wave 4 as declared per task |
| 6 | T015, T019, T021 | C05, C06, system | wave 5 as declared |
| 7 | T018 | C06 (integration) | T012, T013, T015, T016, T017 |
| 8 | T020, T022 | C06, system (integration) | T018, T019 and reliability deps |
| 9 | T023 | system | T014, T015, T020, T022 |
| 9-opt | T025, T027 | system, C02 | T022, T027 deps |
| 10 | T024 | system | T021–T023 |
| 11 | T026 | system (release) | T001 gates, T020, T024 |

Full per-task dependency/gate detail lives in each task file (`docs/tasks/T###-*.md`), not here.

## Human approval gates

Unchanged from v0.1: approve PRD before implementation scope is stable; supply/verify official inputs in T001 (now scoped by named gate class); approve dependency lock in T002; authorize public endpoint exposure and cross-team terms before live play; authorize Gmail OAuth/first real report; approve PLANQ-003/004 before a live external call; verify submission evidence in T026.

## Risks

Unchanged in substance from v0.1 (byte-level integrity mismatch, local-truth leak, retry duplicates, false clean audit, report inconsistency, secret exposure, overengineering); mitigations now live in the owning component PLAN rather than one flat table.

## Unresolved decisions

OPEN-001, 002, 004, 006, 007, 008, 009, 011 (all `official_status: OPEN`); OPEN-003, 010 (`LATE_RUNTIME_INPUT`); OPEN-005 (`RESOLVED_LOCALLY`, narrowed scope — see `docs/spec/OPEN_QUESTIONS.md`); PLANQ-001…008 (team-owned implementation choices).
