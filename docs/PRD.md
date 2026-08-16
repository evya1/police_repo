---
artifact: prd
id: PRD-FINAL-P2P
status: draft
version: 0.4
owner: project-team
source_spec_version: "3.0.0"
updated: 2026-08-16
---

# Product Requirements: Distributed Police/Thief System

## Summary

Build two independently deployable autonomous peers, Police and Thief, that play one decentralized pursuit game over public FastMCP connections without a central judge. Each peer reasons from local truth, opponent scent, and natural-language hints; cryptographic commitments, replayable logs, and independent signed reports make outcomes auditable.

This PRD owns intent and required behavior at system scope. `docs/spec/CANONICAL_REQUIREMENTS.md` owns the repository-local normalized requirement statements and official evidence. `docs/components/*/PRD.md` own what must be true for each major system area; `docs/mechanisms/*.md` own a small number of important algorithms. Role PLANs and component PLANs own implementation strategy; tasks own execution state.

## Problem and context

Two mutually distrustful implementations must interoperate under partial observability, network failure, and asymmetric game abilities. The system must preserve game legality and evidence without sharing live state or relying on a central authority, then produce independently verifiable league and submission artifacts.

## Actors

- Police peer: pursues, may place barriers, maintains a belief about the Thief, and reports independently.
- Thief peer: evades, maintains a belief about Police, responds truthfully to capture verification, and reports independently.
- Opposing team: negotiates shared configuration and provides the remote peer.
- Project team: develops the two greenfield repositories and approves product changes.
- Runtime Orchestrator: the local peer's single subsystem gateway and lifecycle coordinator.
- Workflow orchestrator: owns PRD/PLAN/dependency reconciliation and validates worker handoffs, assembling each worker's bounded context from a task's declared component/mechanism/contract references rather than the whole planning corpus.
- Lecturer/evaluator: receives reports, accesses repositories, evaluates evidence, and applies league normalization.

## Goals

- G-001: Deliver a legal, interoperable, decentralized six-sub-game series between independently running peers.
- G-002: Ensure both roles make legal decisions under partial observability using scent, belief, and natural-language evidence.
- G-003: Make every accepted move and final result cryptographically auditable.
- G-004: Survive bounded network/model failures without silent deadlock or lost evidence.
- G-005: Produce submission-ready repositories, documentation, and independently sent machine-readable reports.
- G-006: Meet the authorized software-quality thresholds without confusing excellence criteria with project validity.
- G-007 *(added in the bounded-context migration)*: Let a human or agent worker implement one bounded task from its declared context alone, without loading the full System PRD, System PLAN, canonical register, and task graph.

## Non-goals

- NG-001: A central game server, shared-memory simulator, or omniscient live observer.
- NG-002: Requiring reinforcement learning or a paid/cloud LLM.
- NG-003: Allowing an LLM to bypass deterministic legality checks.
- NG-004: Reconstructing missing official JSON or Word templates and presenting them as official.
- NG-005: Implementing speculative plugins, microservices, databases, or distributed ledgers.
- NG-006: Fabricating screenshots, benchmark results, league outcomes, token costs, or completed-task evidence.
- NG-007: Defining the lecturer's league-normalization formula.
- NG-008: Treating this planning scaffold as application implementation or completion evidence.
- NG-009 *(added in the bounded-context migration)*: Replacing this file-based planning system with a third-party workflow framework, ticketing tool, or orchestration engine.

## Major system areas

The system decomposes into six components, registered with owned requirement IDs, tasks, contracts, and gates in `planning/COMPONENTS.md`: **C01** Game Core & Configuration, **C02** Perception & Strategy, **C03** Peer Protocol & Integrity, **C04** Runtime & Reliability, **C05** Observability & Replay, **C06** Reporting & League. Submission, cross-cutting quality, and repository-wide prohibitions (SEC-010, OBS-007, SUB-*, most QR-*) stay at system scope rather than folded into one component.

## System / user scenarios

### US-001: Negotiate and lock a series

Given two remote teams and the official parameter statuses, when both sides agree on shared configuration and scent semantics, then byte-identical game terms and their integrity evidence are locked before play. (C01, C02, C03)

### US-002: Execute a legal turn

Given the local peer owns the turn, when its strategy consumes local state, opponent scent, and a verbal hint, then it selects a legal role action, commits before revealing, transmits through FastMCP, and records evidence. (C01, C02, C03, C04)

### US-003: Handle a failed remote request

Given an MCP request has an expiry, when no valid response arrives by the deadline, then bounded retry/recovery policy runs and the peer either resumes or closes the turn as a technical failure without indefinite waiting. (C03, C04)

### US-004: Detect capture and tampering

Given a capture condition or final audit, when the relevant evidence is verified, then truthful capture is scored; any commitment mismatch yields TAMPERED and the required sanction. (C01, C03)

### US-005: Observe without leaking truth

Given a local GUI, when a role watches live play, then it sees only its own position, local turn state, and belief heatmap; when it opens Replay, it can navigate and verify historical steps. (C05)

### US-006: Close and report a match

Given a completed, mutually audited match, when both teams agree on the result, then each independently sends a signed JSON attachment to the official recipient through a protected send-only Gmail flow. (C06)

### US-007: Prepare submission

Given implementation evidence exists, when the team prepares both repositories, then each contains the required academic/user documentation, sibling link, safe configuration history, and annotated submission tag, and each member submits the official form separately. (system scope)

### US-008: Implement one bounded task *(added in the bounded-context migration)*

Given a claimed task, when a worker reads `AGENTS.md`, the task file, and only the task's declared `context_files`/requirement/OPEN/input IDs, then the worker has everything needed to implement and verify the task's `write_set` without reading the System PRD, System PLAN, or unrelated component documents.

## Functional requirements

The functional contract is the canonical requirement set: ARCH-001..009, GAME-001..014, NET-001..005, STRAT-001..009, SEC-001..010, CFG-001..010, OBS-001..007, REPORT-001..013, LEAGUE-001..007, SUB-001..012. There are 96 project-behavior/submission requirements. Any conflict is governed by `docs/spec/OPEN_QUESTIONS.md`; downstream artifacts may not choose silently. Each requirement's primary-owning component is recorded in `docs/spec/TRACEABILITY.md`; this PRD does not restate requirement text.

## Quality requirements

Quality requirements are QR-001..019 (19 criteria). Their authority labels are part of the contract: a quality threshold or excellence criterion is not silently converted into a game-validity condition.

## Success criteria

- SC-001: Two separate processes with isolated configuration complete a six-sub-game series over public FastMCP without shared live state.
- SC-002: Contract tests prove all fixed/default parameter semantics and every movement, barrier, capture, survival, and scoring rule.
- SC-003: Tests prove the configured scent emission/decay semantics and show that belief updates influence both roles' legal decisions.
- SC-004: Every recorded step passes Commit-Reveal verification; a one-byte mutation deterministically produces TAMPERED and the required technical-loss path.
- SC-005: Failure tests show each network wait is bounded and Watchdog recovery preserves usable evidence.
- SC-006: Live GUIs expose only local truth; Replay navigates both directions and verifies every step.
- SC-007: Each team sends a schema-valid signed JSON result independently through `gmail.send`, protected by rate limiting and DOS lockout; live sending occurs only at an explicit human gate.
- SC-008: At least two counted matches against different teams are documented, with no more than one counted match per opponent and no more than ten overall.
- SC-009: Both repositories pass Ruff, tests, at least 85% coverage, repository audits, secret checks, and the 150-code-line threshold at submission.
- SC-010: Both submission READMEs contain only real screenshots/results and link to one another; the annotated `v1.0-submission` tags resolve to the reported commits.
- SC-011 *(added in the bounded-context migration)*: A `component`-typed task's declared `context_files` fully suffice for implementation, verified by `scripts/check_planning_graph.py` finding zero missing-context issues across all 29 tasks in both repositories.

## Constraints

- Official project specification version 3.0.0 controls product/submission behavior.
- Appendix F controls all quantitative values and statuses.
- The official software-quality guide controls quality classifications.
- `docs/spec/PRD_PLAN_TODO_AGENT_WORKFLOW.md` controls planning organization and change flow, including the two-level (system/component) model.
- Repositories are GREENFIELD; no implementation status is implied.
- Private personal information and credentials are prohibited; placeholders are used until confirmed.

## Assumptions and dependencies

- Python and uv are the planned implementation environment, subject to dependency-selection tasks.
- Public reachability requires a team-selected tunneling mechanism and a remote opponent.
- Gmail automation requires local OAuth credentials and explicit human authorization.
- Official JSON templates/schemas, Word form, signing-key procedure, valid eight-character final-project group code, and repository URLs must be supplied later; team name/number and GitHub handles are confirmed non-secret inputs.

## Risks

- Missing schemas may cause interoperability drift if implementation starts prematurely.
- Ambiguous Minimum directions can produce incompatible rate/network settings (narrowed — see OPEN-005 reclassification in `docs/spec/OPEN_QUESTIONS.md`).
- Report-sanction conflict can cause inconsistent scoring.
- Incorrect canonical serialization can make honest commitments unverifiable.
- Network tunnels and OAuth flows introduce external operational failure modes.
- Overengineering can delay the legal core; under-testing can hide protocol divergence.
- Bounded task context can drift from actual repository state if a task's declared `context_files` are not kept current as components evolve; the planning-graph validator and wave-reconciliation step mitigate this.

## Open questions

- OPEN-001 through OPEN-011 in `docs/spec/OPEN_QUESTIONS.md` are active; each now carries both an `official_status` and an `implementation_status`, so an unresolved question blocks only the scope it actually governs.
- OPEN-001, OPEN-004, OPEN-006, and OPEN-007 block production interoperability or reporting decisions at specific criteria, not whole components.
- OPEN-002 and the unresolved fields in OPEN-003 block final submission packaging, not core development.
- OPEN-005's directional ambiguity is reclassified `implementation_status: RESOLVED_LOCALLY`; `official_status` remains OPEN. See the reclassification note in `docs/spec/OPEN_QUESTIONS.md`.
- OPEN-009's saturation/merge ambiguity is reclassified `implementation_status: DRAFT_CONTRACT_NONOFFICIAL` by the kit-first interoperability decision; `official_status` remains OPEN. Scent implementation, default-profile selection, and model-lock declaration proceed against the approved profile; the official reading is confirmed before counted play. See the reclassification note in `docs/spec/OPEN_QUESTIONS.md`.

## Approval and change history

| Version | Date | Status | Change | Approval |
|---|---|---|---|---|
| 0.1 | 2026-08-14 | draft | Initial canonical PRD reconstructed from authorized sources | Pending project-team review |
| 0.2 | 2026-08-15 | draft | Recorded OPEN-011 (move-cap-versus-survival-threshold termination ambiguity), discovered while decomposing stage-1 board logic into T003/T004/T028/T029; no requirement was added, removed, or normatively changed, so no Change Request applies | Orchestrator edit, still pre-approval |
| 0.3 | 2026-08-15 | draft | Bounded-context migration (Issue #1 / Issue #3): moved mechanism-level detail out to component/mechanism PRDs, added G-007/NG-009/US-008/SC-011, reclassified OPEN-005's implementation-side scope. No requirement was added, removed, or normatively changed, so no Change Request applies | Orchestrator edit, still pre-approval |
| 0.4 | 2026-08-16 | draft | Kit-first interoperability profile: recorded the team-approved default runtime profile (`reference-v3`, `subtractive_chebyshev_v1`, `belief`, unbound smell) with `multiplicative_book_v1` additionally supported, and reclassified OPEN-009's implementation-side scope. `official_status` for OPEN-009 is unchanged and still OPEN. No requirement was added, removed, or normatively changed, so no Change Request applies | Orchestrator edit, still pre-approval |

After approval, every material behavior/scope change requires a Change Request naming affected requirement IDs, source/authority, impact, approval, and resulting PRD version, followed by PLAN/task reconciliation.
