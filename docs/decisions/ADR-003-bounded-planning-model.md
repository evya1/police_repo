---
artifact: adr
id: ADR-003
status: accepted
date: 2026-08-15
owners: orchestrator
related_requirements: []
related_tasks: [T001, T002, T003, T004, T005, T006, T007, T008, T009, T010, T011, T012, T013, T014, T015, T016, T017, T018, T019, T020, T021, T022, T023, T024, T025, T026, T027, T028, T029]
supersedes:
---

# ADR-003 — Bounded two-level planning model

Use an ADR only for a sufficiently important and durable technical design decision. Official-input receipt belongs in the Input Register, product/requirement changes belong in a Change Request, and execution work belongs in a task. This decision changes planning organization only; no canonical requirement, OPEN ID, or task ID was added, removed, or normatively changed by it, so no Change Request applies. Tracked by GitHub Issue #3.

## Context

Multi-component system development requires disciplined planning boundaries to prevent cognitive overload, false coupling, and artificial serialization across engineering tasks.

The planning architecture addresses several core structural needs:
- **Task-bounded context:** Workers (human contributors and autonomous agents) need a justified, task-bounded context containing only the exact specifications and source files required for their specific assigned scope, rather than loading the entire repository planning tree.
- **Scope separation:** System-wide requirements and component-specific design have distinct scopes. System specifications define product intent, global invariants, and shared interfaces, while component specifications govern local mechanisms, algorithms, and modular implementations.
- **Independent execution:** Independent work on decoupled subsystems must proceed in parallel without requiring workers to load unrelated planning material or wait on unrelated subsystem decisions.
- **Precision gating:** Readiness gates must block the exact criterion they govern rather than coarsely blocking entire tasks across broad classes of external inputs or dependencies.
- **Deterministic validation:** Tooling must be able to deterministically validate component requirement ownership, dependency paths, declared context boundaries, and fine-grained gate readiness.

## Decision

Adopt a two-level planning model with explicit component ownership, boundary contracts, and fine-grained gates:

- **System and component hierarchy:** A concise System PRD (`docs/PRD.md`) and System PLAN (`docs/PLAN.md`) state product intent and system-wide architecture; six components (`docs/components/README.md`) each get a focused PRD (what must be true) and PLAN (how it is built, authored substantively for C01–C03 and left deliberately shallow for C04–C06 until their owning task claims them); a small number of important algorithms (five shared, two role-specific) get a dedicated mechanism PRD (`docs/mechanisms/`); six explicit boundary contracts (`docs/contracts/`) state exactly what one component may assume about another.
- **Bounded task context:** Every task's frontmatter declares a bounded `context_files` list, a `read_set`/`write_set` split, and a `gates:` list that distinguishes three blocking levels (`start`, `criterion`, `integration`).
- **Precision input gates:** Official input intake (T001) is decomposed into four named input-gate classes (`G-OFFICIAL`, `G-PROFILE`, `G-TEAM`, `G-LIVE`) in `docs/spec/OPEN_QUESTIONS.md`. Individual tasks cite the specific gate they actually need, at the specific criterion it actually blocks, rather than depending monolithically on all of T001.
- **Single-component requirement ownership:** Every requirement has exactly one primary-owning component, recorded in `docs/spec/TRACEABILITY.md`'s `Primary component` column, so a worker can find the one PRD that owns a given ID without scanning the whole register.

## Alternatives considered

- **Leave a single monolithic PLAN model and rely on worker discipline to read only the relevant section.** Rejected: a single monolithic document with no addressable sub-boundaries cannot be partially read with confidence, and nothing prevents accidental cross-mechanism coupling.
- **One PRD/PLAN per task instead of per component.** Rejected: over-fragments planning into as many documents as there are tasks (29), creating excessive micro-planning and duplicating requirement text across closely related neighboring tasks.
- **Adopt a third-party workflow/ticketing framework (Jira-style, LangGraph-style orchestration) to get bounded context.** Rejected: the file-based planning system already carries stable IDs, traceability, write-set discipline, and human governance gates that a generic framework would either duplicate or override; the actual gap was documentation granularity and dependency-edge precision, not a missing tool.
- **Keep T001 as a single monolithic `depends_on` edge and rely on task authors to note in prose which part of T001 they actually need.** Rejected: prose notes are not mechanically checkable by `scripts/check_planning_graph.py`, and a monolithic flat edge produces false blocking across independent criteria.

## Consequences

Positive:
- Tasks with independent prerequisites (such as T004, T008, T009, T017, T028) can proceed in parallel once foundational dependencies (such as T003) complete, with nothing waiting on unneeded input classes; local Game Core, strategy-against-fakes, and local peer/MCP work all proceed while official artifacts and opponent endpoints remain outstanding.
- A component-scoped task's bounded context is a handful of declared files instead of the whole repository.
- `scripts/check_planning_graph.py` mechanically verifies that a task's declared context exists and that no requirement is claimed by two components.

Negative:
- More files to keep in sync — mitigated by `docs/components/*/PRD.md`, `docs/mechanisms/`, and `docs/contracts/` being shared and verified byte-identical between role repositories.
- C04–C06 PLANs are intentionally shallow until their owning task claims them, which means a worker reading ahead of schedule will find a shallow document — this is by design, not an oversight, per `docs/spec/PRD_PLAN_TODO_AGENT_WORKFLOW.md` §10's prohibition on micro-planning stale detail.

Interoperability and requirements:
- No canonical requirement text changed; `docs/spec/TRACEABILITY.md` and `docs/spec/OPEN_QUESTIONS.md` define component ownership and input-gate classes without altering requirement definitions.
- Task frontmatter fields (`id`, `status`, `priority`, `implements`, `depends_on`, `parallel_safe`, `claimed_by`, `claim_expires_at`, `write_set`, `risk`) keep their exact names and meanings.

## Validation

- `scripts/run_quality_gates.py` passes unchanged (task-graph, docs-present, and link checks all green).
- `scripts/check_planning_graph.py` passes: 29 tasks, 6 components, every `context_files` path exists, every requirement has exactly one primary owner, dependency graph acyclic.
- `diff docs/PRD.md` against the sibling Thief repository is empty (byte-identical System PRD preserved).
- `diff -r docs/spec` against the sibling repository is empty (five shared registers byte-identical).

## Approval

- Decision owner: orchestrator
- Approved by: project team (pending — recorded pre-approval)
- Approval date: 2026-08-15
