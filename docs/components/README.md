---
artifact: component-register
id: COMPONENTS
status: draft
owner: orchestrator
updated: 2026-08-15
---

# Component Register

Six major system areas, adopted after inspecting the current PRD, PLANs, canonical requirements, task graph, and OPEN questions (bounded-context migration, Issue #1 / Issue #3). Submission/compliance/release work is deliberately **not** folded into C06; it stays at System scope with task types `governance`/`verification`/`release`, so C06 remains focused on reporting and league mechanics rather than becoming a catch-all.

Each component has exactly one PRD (what must be true) and one PLAN (how it is currently built) per role repository. Component PRDs are bundle-mastered and byte-identical between Police and Thief, because what each component must observably do is shared. Component PLANs are role-owned, because how each role builds it may differ even when the contract is shared.

## Authoring depth

Full PRDs are authored for all six components. Substantive PLANs are authored for **C01, C02, C03** — the components with tasks open or nearly open. **C04, C05, C06 PLANs are deliberately shallow**: purpose, boundary, known risks, and an explicit marker that internal design is authored by the owning task once claimed. This follows the existing methodology's prohibition on micro-planning stale future detail (`PRD_PLAN_TODO_AGENT_WORKFLOW.md` §10) — C04–C06 internals depend on OPEN-001/004/007/008, which are not expected to resolve before C01–C03 work completes.

## Register

| ID | Name | Purpose | Primary-owned requirements | Existing tasks | Contracts owned | OPEN/input gates | PRD | PLAN |
|---|---|---|---|---|---|---|---|---|
| C01 | Game Core & Configuration | Board, legal actions, barriers, capture, scoring; shared/private configuration precedence and Appendix F status validation | ARCH-001,002,003,009; GAME-001…014; CFG-001…010 (28) | T003, T004, T028, T029 | CT-01 | OPEN-011 (criterion), OPEN-005 (criterion, reclassified), OPEN-001 (via ADR-001 shape) | shared | role, substantive |
| C02 | Perception & Strategy | Scent arithmetic, belief distribution, role decision policy, verbal-hint boundary | ARCH-007; STRAT-001…009 (10) | T005, T006, T007, T027 | CT-02 | OPEN-009 (criterion: model_lock) | shared core; M-03/M-04 role-specific | role, substantive |
| C03 | Peer Protocol & Integrity | FastMCP surface, envelopes, Commit-Reveal, audit, Step 0, inbound delivery safety | NET-001…004; SEC-001…009 (13) | T008, T009, T012, T013 | CT-03, CT-04 | OPEN-007 (criterion: cross_peer_vectors), G-LIVE (criterion: public_endpoint) | shared | role, substantive |
| C04 | Runtime & Reliability | Orchestrator state machine, legal transitions, deadlines, retry journal, watchdog, recovery | ARCH-004,005,006,008; NET-005 (5) | T010, T011 | CT-05, CT-06 | none blocking local work | shared | role, shallow |
| C05 | Observability & Replay | Local-truth Live GUI, belief heatmap, immutable verified Replay | OBS-001…006; QR-017 (7) | T014, T015 | (consumer of CT-05) | none blocking local work | shared | role, shallow |
| C06 | Reporting & League | Official artifact schemas, Gatekeeper/Gmail, signed pipeline, series/scoring, pairing guards | REPORT-001…013; LEAGUE-001…007; QR-008,018 (22) | T016, T017, T018, T019, T020 | (consumer of CT-04, CT-06) | OPEN-001 (start), OPEN-004 (criterion), OPEN-008 (criterion), G-LIVE (criterion: pairing_preflight) | shared | role, shallow |
| — | System scope | Intake coordination, coverage, docs/evidence, compliance audit, optional study, release | SEC-010; OBS-007; SUB-001…012; QR-001…007,009…016,019 (30) | T001, T021, T022, T023, T024, T025, T026 | (integration/verification of all) | all gate classes | System PRD | System PLAN |

Namespace check against `TRACEABILITY.md`: 28+10+13+5+7+22+30 = 115 requirement IDs, matching the canonical register exactly.

## Requirement ownership rule

Every canonical requirement ID has **exactly one** primary-owning component or `system` scope, recorded in `TRACEABILITY.md`'s `Primary component` column and enforced by `scripts/check_planning_graph.py` (both role repos). A component may still be listed as `consumer`, `affected`, or `verification owner` for a requirement it does not primarily own — see each component PRD's "Requirements consumed / affected" section — but never as a second primary owner.

## Mechanism PRDs

Seven mechanism PRDs are authored under `planning/mechanisms/`; five are shared (M-01, M-02, M-05, M-06, M-07) and two are role-specific (M-03 Police strategy, M-04 Thief strategy, each authored only in its own role repository). See each mechanism PRD for why it earns separate treatment instead of being folded into its owning component PRD.

## Boundary contracts

Six contracts are authored under `planning/contracts/`, all shared and byte-identical between Police and Thief. See `planning/contracts/` and each contract file for owner, consumers, and governing IDs.
