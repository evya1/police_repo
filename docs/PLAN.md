---
artifact: plan
id: PLAN-POLICE
status: draft
version: 0.4
derived_from: PRD-FINAL-P2P@0.5
owner: orchestrator
updated: 2026-08-16
---

# Police System PLAN

Mechanism-level detail — the turn-adjudication flowchart, state model, compatibility decision matrices, and per-mechanism technical decisions — is defined in the six component PLANs under `docs/components/` and the mechanism PRDs under `docs/mechanisms/`. This System PLAN stays concise: system-wide boundaries, dependency direction, shared contracts, security/config ownership, lifecycle, integration order, and system-level gates.

**Version 0.3** (supersedes v0.2). Adds TD-06, recording the selected runtime interoperability profile and the second supported scent model. No component boundary, contract, dependency edge, or execution wave changed.

**Version 0.4** (supersedes v0.3). Records the runtime baseline decision (PLANQ-002), the verification ladder, and the current implementation state of the C01 foundation. No component boundary, contract, dependency edge, or execution wave changed.

## Approach summary

Build one autonomous Police peer as six components (`docs/components/README.md`) around a pure local domain core (C01), perception/strategy (C02), peer protocol/integrity (C03), a thin runtime orchestrator (C04), local-truth observability (C05), and reporting/league (C06), connected only through the six boundary contracts (`docs/contracts/`). Requirement IDs refer to `docs/spec/CANONICAL_REQUIREMENTS.md`; this PLAN selects system-level technical strategy and does not redefine intent.

## Repository structure

The tree below is the target layout. A path in it is not evidence that the path exists; directories are created only by the task that owns them.

What exists today on the integration branch is the C01 foundation: shared domain and configuration modules under `common/`, a role re-export surface under `src/police_peer/domain/`, and the committed shared game contract at `config/game.json`, with unit tests under `tests/unit/domain/`. See `docs/TODO.md` for the per-task implementation state.

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

See the project-level integration plan (not part of this repository; reasoning synchronized below) for the full named-gate table. In order: component-local gates (per component PLAN's local test strategy) → `local_mcp_smoke`/`stage1_gate` (C01+C03 local proof) → `orchestration_integration` (C04 sequencing) → `cross_peer_vectors` (gated by OPEN-007) → `live_interop` (T022, the full interoperability/recovery gate) → `pairing_preflight`/`report_reconciliation` (final pre-counted-match gates). Each owning task proves its own compatibility surface earlier — T005 both scent profiles, T008 its byte-level primitives, T009 the `reference-v3` contract — so `live_interop` re-runs those surfaces as a system rather than exercising them for the first time.

## System verification

Full-series verification is the union of every named integration gate passing plus the System-scope tasks: T021 (property/coverage closure), T023 (documentation/evidence), T024 (compliance audit), T026 (release). No task is treated as a trusted integration dependency before its component-local gate passes.

## Verification ladder

Confidence is earned in this order; a stage is entered only after the stage before it passes. Gate names refer to the project-level integration plan; task IDs refer to `docs/tasks/`.

| Stage | What it proves | Owning tasks | Gate |
|---|---|---|---|
| 1. Deterministic unit and golden-vector verification | Domain rules, scent profiles, canonical bytes, and commitments are correct and reproducible in one process | T004, T005, T008, T019, T021 | component-local |
| 2. Independent local two-process protocol smoke test | Two separate processes complete a turn cycle over the real adapter with no endpoint, tunnel, or opponent | T009, T029 | `local_mcp_smoke`, `stage1_gate` |
| 3. Practice-peer full-series test | A complete six-sub-game series sequences, settles, and audits end to end | T010, T011, T019, T022 | `orchestration_integration` |
| 4. Artifact validation | Declaration, configuration, log, and result artifacts validate, reconcile, and carry consistent identifiers | T016, T018 | `report_reconciliation` |
| 5. Network reachability and readiness | The public endpoint and tunnel procedure are reachable and stable, using real values once `G-LIVE` is satisfied | T009, T020 | `pairing_preflight` |
| 6. Friendly external game | An uncounted series against an independently written external peer settles clean in both role directions | T022 | `live_interop` |
| 7. Counted game | A counted match runs only after every stage above passes and every counted-play confirmation is recorded | T020, T026 | `pairing_preflight` + human authorization |

Stages 6 and 7 additionally require the counted-play confirmations named in `docs/spec/OPEN_QUESTIONS.md`: the scent profile (OPEN-009), the series schedule and tie rule (OPEN-008), the report sanction (OPEN-004), and the team/runtime/submission metadata (OPEN-010).

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

- **Choice:** implement from canonical requirements and approved contracts; derive edge-case and compatibility tests from explicit project ambiguities, using the differential-test pattern where a mechanism PRD still carries a compatibility matrix (M-05, M-07) and a named implementation profile where one has been approved instead (M-01, CT-03 — see TD-06).
- **Reason:** preserves artifact authority and exposes interoperability failures without introducing unsupported schemas or hidden assumptions.

### TD-04 — Minimal Python application shape (retained from v0.1)

- **Choice:** the local, non-standard label `PY-2-minimal` — a maintained Python application with meaningful deterministic rules and external I/O, pure domain core, thin adapters, manual dependency wiring, plain functions for stateless behavior, classes only when they own state/invariants/lifecycle.
- **Reason:** the system has multiple external boundaries and substantial rules, but no demonstrated need for transaction-heavy abstractions or a general extension framework.
- **Consequences:** a DI container, generic Repository/Unit of Work, domain-event bus, or CQRS requires a concrete need and an approved PLAN update or ADR.

### TD-05 — Negotiated nested shape for the shared game contract (retained from v0.1)

- **Choice:** adopt the nested-section `config/game.json` layout recorded in `docs/decisions/ADR-001-shared-game-contract-shape.md`, authored and validated by T028/T003.
- **Reason:** CFG-001/CFG-004 fix which values the contract must carry, not its JSON shape; this is our own negotiable engineering choice, explicitly labeled non-official pending OPEN-001.

### TD-06 — Operational interoperability profile

- **Choice:** one selected runtime interoperability profile — `wire_shape: reference-v3`, `scent_model: subtractive_chebyshev_v1`, `info_mode: belief`, unbound smell behavior, thief-first turn order — with `multiplicative_book_v1` additionally supported, recorded in `docs/decisions/ADR-004-operational-interoperability-profile.md`.
- **Alternatives:** the multiplicative profile as the sole or default model; the subtractive profile only, dropping the multiplicative one; selecting nothing until OPEN-009 is officially answered.
- **Reason:** the official requirements leave scent saturation, merge, update order, wire keys, and turn order undefined, and each needs one deterministic value before two peers can exchange a first message. `subtractive_chebyshev_v1` is the arithmetic `reference-v3` transmits, so a run starts without renegotiating scent physics.
- **Consequences:** two scent implementations behind one interface with configuration-driven selection; the selected model is registered, hashed, and declared; both models are vector-tested; OPEN-009 stays officially OPEN but does not block implementation or model locking; strategy and domain logic stay behind the adapter boundary.

### TD-07 — Runtime dependency baseline

- **Choice:** Python 3.12 as the CI/runtime baseline with the declared range `>=3.12`; FastMCP as a direct runtime dependency at `fastmcp>=3.4,<4`; the existing `pytest`/`pytest-cov`/`ruff`/`pre-commit`/`pyyaml` tooling preserved; `uv` as the package/dependency manager and not an application dependency. Recorded as PLANQ-002 in `docs/spec/OPEN_QUESTIONS.md`.
- **Alternatives:** an unpinned FastMCP dependency; adopting the unreleased 4.x line; widening or narrowing the Python range speculatively.
- **Reason:** the `<4` bound keeps the runtime on the current stable major line while its successor is still prereleased, and the range was verified to resolve against `requires-python = ">=3.12"`.
- **Consequences:** T002 executes this baseline and commits the validated lock; GUI, Gmail, and any optional model-provider dependency stay owned by PLANQ-007, PLANQ-005, and PLANQ-003 respectively.

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

Approve the PRD before implementation scope is stable; supply and verify official inputs in T001 (scoped by named gate class); review the dependency lock produced by T002 against the recorded PLANQ-002 baseline; authorize public endpoint exposure and cross-team terms before live play; authorize Gmail OAuth and the first real report; approve the provider and budget under PLANQ-003 before any live external call; confirm the team, runtime, and submission metadata under OPEN-010 before counted play and submission; verify submission evidence in T026.

## Risks

Unchanged in substance from v0.1 (byte-level integrity mismatch, local-truth leak, retry duplicates, false clean audit, report inconsistency, secret exposure, overengineering); mitigations now live in the owning component PLAN rather than one flat table.

## Unresolved decisions

OPEN-001, 004, 006, 007, 008, and 009 remain `official_status: OPEN` with recorded operational conventions that do not block the completed implementation; OPEN-005 is `RESOLVED_LOCALLY`; OPEN-003 and OPEN-010 are late runtime inputs. PLANQ-002, 003, 004, 005, 007, and 008 are resolved; PLANQ-001 and 006 are partially resolved. Full detail is in `docs/spec/OPEN_QUESTIONS.md`.
