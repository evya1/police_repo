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

The pre-migration planning model had one PRD and one 339-line PLAN per repository. A worker claiming any task was expected to have effectively read the whole PLAN, because mechanism-level detail (the turn-adjudication flowchart, the full state model, every compatibility decision matrix) lived in that single document rather than near the task that actually needed it. `docs/TODO.md` showed 28 of 29 tasks as `blocked`, and T001 — a single official-input-intake task — sat as a `depends_on` edge on T005, T009, T016, T019, T020, and T026, even though those six tasks needed different classes of information (an official schema, a team decision, a live opponent) that become available at different times.

Two people and/or agents working on separate parts of the system therefore could not safely start in parallel: everyone's mental model of "what do I need to read" was "everything," and the dependency graph funneled almost every task through one intake task regardless of what it actually needed from that intake.

## Decision

Adopt a two-level planning model. A concise System PRD/PLAN states product intent and system-wide architecture; six components (`docs/components/README.md`) each get a focused PRD (what must be true) and PLAN (how it is built, authored substantively for C01–C03 and left deliberately shallow for C04–C06 until their owning task claims them); a small number of important algorithms (five shared, two role-specific) get a dedicated mechanism PRD; six explicit boundary contracts (`docs/contracts/`) state exactly what one component may assume about another. Every task's frontmatter now declares a bounded `context_files` list, a `read_set`/`write_set` split, and a `gates:` list that distinguishes three blocking levels (`start`, `criterion`, `integration`) instead of one flat `depends_on` edge to a mega-task.

T001 is decomposed into four named input-gate classes (`G-OFFICIAL`, `G-PROFILE`, `G-TEAM`, `G-LIVE`) in `docs/spec/OPEN_QUESTIONS.md`. Individual tasks cite the specific gate they actually need, at the specific criterion it actually blocks, rather than depending on all of T001.

Every requirement now has exactly one primary-owning component, recorded in `docs/spec/TRACEABILITY.md`'s `Primary component` column, so a worker can find the one PRD that owns a given ID without scanning the whole register.

## Alternatives considered

- **Leave the single-PLAN model and rely on worker discipline to read only the relevant section.** Rejected: a 339-line document with no addressable sub-boundary cannot be partially read with confidence, and nothing prevented accidental cross-mechanism coupling.
- **One PRD/PLAN per task instead of per component.** Rejected: over-fragments planning into as many documents as there are tasks (29), reintroducing the "one PRD per class/helper" anti-pattern the migration brief explicitly warned against, and duplicating requirement text across near-identical neighboring tasks.
- **Adopt a third-party workflow/ticketing framework (Jira-style, LangGraph-style orchestration) to get bounded context "for free."** Rejected: the existing file-based planning system already carries stable IDs, traceability, write-set discipline, and human governance gates that a generic framework would either duplicate or override; the actual gap was documentation granularity and dependency-edge precision, not a missing tool.
- **Keep T001 as a single `depends_on` edge and rely on task authors to note in prose which part of T001 they actually need.** Rejected: prose notes are not mechanically checkable by `scripts/check_planning_graph.py`, and the previous state (28/29 tasks blocked) shows the flat edge already produced the wrong readiness computation in practice.

## Consequences

Positive: T004, T008, T009, T017, T028 can now open in parallel once T003 completes, with nothing waiting on T001; local Game Core, strategy-against-fakes, and local peer/MCP work all proceed while official artifacts and opponent endpoints remain outstanding. A `component`-typed task's bounded context is now a handful of files instead of the whole repository. `check_planning_graph.py` can mechanically verify that a task's declared context exists and that no requirement is claimed by two components.

Negative: more files to keep in sync — mitigated by `docs/components/*/PRD.md`, `docs/mechanisms/`, and `docs/contracts/` being shared and verified byte-identical between role repositories. C04–C06 PLANs are intentionally incomplete until their owning task claims them, which means a worker reading ahead of schedule will find a shallow document — this is by design, not an oversight, per `docs/spec/PRD_PLAN_TODO_AGENT_WORKFLOW.md` §10's prohibition on micro-planning stale detail.

Interoperability and migration: no canonical requirement text changed; `docs/spec/TRACEABILITY.md` and `docs/spec/OPEN_QUESTIONS.md` gained columns/fields but no row was removed. Every pre-existing task frontmatter field (`id`, `status`, `priority`, `implements`, `depends_on`, `parallel_safe`, `claimed_by`, `claim_expires_at`, `write_set`, `risk`) keeps its exact name and meaning.

## Validation

- `scripts/run_quality_gates.py` passes unchanged (task-graph, docs-present, and link checks all green against the new file set).
- `scripts/check_planning_graph.py` passes: 29 tasks, 6 components, every `context_files` path exists, every requirement has exactly one primary owner, dependency graph acyclic.
- `diff docs/PRD.md` against the sibling Thief repository is empty (byte-identical System PRD preserved).
- `diff -r docs/spec` against the sibling repository is empty (five shared registers byte-identical).
- Full exact command output is recorded in the project's migration validation record.

## Approval

- Decision owner: orchestrator
- Approved by: project team (pending — recorded pre-approval per the two-gate migration workflow)
- Approval date: 2026-08-15
