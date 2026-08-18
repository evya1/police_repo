# PRD / PLAN / TODO Agent Workflow

> Repository execution copy of the approved planning methodology. This file contains the repository-facing rules needed for standalone work and preserves the methodology's artifact ownership, stable-ID, change-control, task, orchestration, and verification semantics.

## 1. Artifact ownership

| Artifact | Owns | Must not become |
|---|---|---|
| System `PRD.md` | Product intent, actors, goals, scope, requirements (by ID, not restated), success criteria, constraints, assumptions, risks, open questions, approval history | Architecture detail, mechanism-level detail, or live task state |
| Component/mechanism `PRD.md` | What must be true for one component/mechanism: purpose, owned requirement IDs, observable behavior, invariants, failure/edge cases, acceptance scenarios, relevant contracts and OPEN/input gates, Definition of Done | A duplicate of the System PRD, or implementation detail |
| System `PLAN.md` | Role-aware system/integration architecture: major boundaries, dependency direction, shared contracts, security boundaries, lifecycle, integration order, system verification | Mechanism-level design or a status board |
| Component `PLAN.md` | How one component is built: internal design, state ownership, alternatives/trade-offs, local test strategy, component-level integration, known risks | A duplicate PRD, or premature detail for a component whose owning task has not started |
| Boundary contract | Owner, consumers, input, output, externally visible invariants, failure behavior, version/compatibility rule, governing requirement IDs | An implicit assumption nobody wrote down |
| `TODO.md` | Compact execution index and progress overview | A second detailed task store |
| `tasks/T###-*.md` | Atomic scope, requirements, dependencies, claim, bounded context, write set, gates, acceptance, verification, plan, handoff, and evidence | A place to invent product requirements |
| `AGENTS.md` | Stable repository rules, commands, permissions, and conventions | Feature-specific scope or task state |
| ADR | A sufficiently important and durable technical decision | Product scope, input receipt, or task state |
| Change Request | A proposed material change to an approved requirement or PRD contract | Input intake, technical choice, or implementation backlog |
| Code and tests | Actual implemented behavior and verification | The sole statement of intended behavior |

Changes flow from PRD to PLAN to TODO/tasks to implementation to evidence — at **both** levels described in §1a. A downstream artifact must not silently redefine an upstream artifact.

## 1a. Two-level planning

The PRD → PLAN → TODO/Tasks → implementation → verification chain now operates at two levels:

1. **System level** — one concise System PRD and one concise System PLAN per role repository, covering the whole product: purpose, actors, major scenarios, system-wide invariants, non-goals, major areas, and end-to-end success criteria. They reference requirement IDs; they do not restate them and do not carry mechanism-level detail.
2. **Component/mechanism level** — a small, fixed set of major system areas (recorded in `planning/COMPONENTS.md`), each with a focused PRD (what must be true) and PLAN (how it is currently built). A small number of important algorithms/mechanisms that cross or deepen a component (e.g. the scent model, Commit-Reveal) get their own dedicated mechanism PRD only when doing so materially reduces ambiguity — not one per class, helper, or file.

A task declares exactly which System/component/mechanism/contract documents and which requirement/OPEN/input/decision IDs it needs (§5). A worker reads only that declared set plus `AGENTS.md` and the task file — never the entire System PRD, System PLAN, canonical register, and task graph by default.

## 2. Stable identifiers and traceability

- Requirements, OPEN items, tasks, ADRs, and Change Requests use stable published IDs.
- Never renumber later IDs to close a gap.
- Tasks and PLAN elements reference canonical requirement IDs instead of copying large requirement prose.
- Traceability flows from requirement to primary-owning component to PLAN design to tasks to verification evidence. Each requirement has exactly one primary-owning component (or `system` scope); other components may consume, be affected by, or verify it, but do not compete for primary ownership. `TRACEABILITY.md`'s `Primary component` column and `planning/COMPONENTS.md`'s ownership table are the source for this relation.
- Removed work keeps its historical ID when history matters; dangling dependencies and links are prohibited.

## 3. Lifecycle and approval gates

The normal lifecycle is discover, specify, clarify, approve PRD, plan, review PLAN, decompose, validate consistency, execute dependency waves, reconcile each wave, verify, and close — applied at the System level first, then within each component as its tasks open.

- Do not skip an explicit human or automated gate merely because work can continue technically.
- Only the orchestrator edits PRD (System or component), PLAN (System or component), contracts, task dependencies/gates, or global TODO structure.
- Workers update only authorized claim/result fields and their declared write sets.
- Approved requirement meaning never changes silently during implementation.

## 4. Event semantics

### Official input arrives

1. Record it in `docs/inputs/INPUT_REGISTER.md` without secret contents.
2. Verify authority, completeness, version, and any safe hash.
3. Update affected `OPEN-*` entries, including both `official_status` and `implementation_status` where the input narrows or closes the implementation-side gate (see §6a).
4. Reconcile derived PLAN, tasks, tests, and traceability when needed.
5. Open a Change Request only if accepting the information materially changes an already-approved canonical product requirement or PRD contract.

### Technical design decision

Use an ADR only when the decision is important and durable enough to preserve. An ADR does not change product scope.

### Product or requirement change

A Change Request is required when a requirement is added, removed, or normatively changed, a binding constraint changes, or the approved PRD contract changes materially. It names affected requirement IDs, motivation, source/authority, impact, approval, and resulting PRD version. After approval, synchronize the canonical register if authorized, both PRDs, PLAN coverage (System and affected components), tasks, tests, and traceability.

### Additional implementation work

Create a new stable task ID. Do not open a Change Request and do not silently expand the active task when product scope is unchanged.

## 5. Task model

Recommended states are `backlog`, `ready`, `claimed`, `in_progress`, `review`, and `done`; exceptional states are `blocked`, `failed`, `cancelled`, and `superseded`.

- `ready` means every `depends_on` task is `done` and no `gates:` entry has `blocks: start` (§6a).
- `blocked` names the concrete `depends_on` task or `gates:` entry with `blocks: start` responsible.
- `done` requires accepted criteria and recorded verification evidence.
- A task has one clear outcome, stable ID, a declared `component` (or `system`), a `task_type`, requirement references, dependencies, a bounded `context_files` list, `read_set`/`write_set`, `gates:`, finite claim, acceptance criteria with stable anchors, verification, just-in-time implementation plan, and handoff contract.
- A task is small enough for one focused worker context and one reviewable change.
- Newly discovered work is reported to the orchestrator for a new task ID.

### Task types

`foundation`, `component`, `integration`, `verification`, `governance`, `release`, with `optional` as an independent boolean modifier. A `component` task's default context is its owning component's PRD/PLAN plus relevant mechanism PRDs and contracts. An `integration` task's default context is the relevant contracts, component acceptance evidence, and integration requirements — not every component's internal PLAN. A `governance` task may receive broader planning context. A `release` task may receive whole-system context.

## 6. Bounded context and write ownership

A task's frontmatter declares exactly what a worker needs:

- `context_files` — the worker's entire required reading beyond `AGENTS.md` and the task file. Every path **must exist** when the task is authored; it is the worker's bounded planning context.
- `read_set` — **additional** read-only scope *outside* the worker's own `write_set` (for example, a public type owned by another component). A worker may always read every path already in its own `write_set`; `read_set` never restricts that. `read_set` paths may name outputs of a future task and are not required to exist yet.
- `write_set` — the paths the worker may create or edit. Paths frequently describe future outputs and are not required to exist yet. `write_set`s must not overlap across tasks claimed to run in the same `parallel_safe` wave.
- `gates:` — see §6a.

### 6a. Gates: three distinguishable blocking levels

A single `gates:` list replaces ad-hoc blocker fields. Each entry has an `id` resolving in the register named by its `kind` (`open` → `OPEN_QUESTIONS.md`; `input` → `INPUT_REGISTER.md`; `input_gate` → the four named classes in `OPEN_QUESTIONS.md`; `decision` → the Implementation Decision Register), a `scope` naming the acceptance-criterion anchor or integration gate it affects, and a `blocks` level:

- `start` — the task cannot be claimed.
- `criterion` — the task can be claimed and implemented; only the named acceptance criterion cannot yet be checked off.
- `integration` — the task can complete locally; it cannot yet serve as a trusted integration dependency at the named integration gate.

**Readiness is exactly:** every `depends_on` task is `done`, and no `gates:` entry has `blocks: start`. `criterion` and `integration` gates never affect readiness; they are checked at their named anchor. This lets many tasks proceed on official-artifact-adjacent work without becoming globally blocked, while still refusing to let an unresolved ambiguity silently pass an acceptance or integration gate.

## 7. Claiming and execution

Before implementation, a worker must:

1. read `AGENTS.md`, the task, its declared `context_files`, and the requirement/OPEN/input/decision IDs it names;
2. verify dependencies and status (§6a readiness rule);
3. claim the task with claimant and finite expiry;
4. confirm exclusive, non-overlapping `write_set` ownership for the wave;
5. write a short implementation plan against current repository state;
6. edit only the declared `write_set` (which is always readable), plus read the declared `read_set`;
7. run focused verification and repository gates, including any `criterion`/`integration` gates the task's acceptance criteria name;
8. return files changed, exact commands/results, acceptance evidence, decisions, deviations, blockers, and proposed follow-up tasks.

The orchestrator validates the handoff against repository state before changing task status.

## 8. Parallel execution

Tasks may run in parallel only when dependencies are satisfied, they do not need one another's intermediate state, `write_set`s do not overlap, shared external resources have a concurrency protocol, claims are exclusive, integration order is known, and one failure cannot make the other task unsafe.

Before each wave, verify readiness (§6a) and write sets. After each wave, validate results, integrate deterministically, run wave-level tests, reconcile PLAN/TODO/tasks/traceability, and stop on blocking failure.

## 9. Safety and permissions

- Apply least privilege and preserve unrelated work.
- Never place credentials, tokens, keys, passwords, private IDs, or secret contents in planning artifacts, code, tests, examples, logs, or the Input Register.
- Destructive, release, public-network, live-email, and submission actions require their stated human gates.
- Report permission failures and blockers; do not bypass controls.
- Do not add third-party code or configuration without verifying license obligations and preserving required notices.

## 10. Verification and consistency

A task is complete only when acceptance criteria, focused tests, required static/build checks, documentation, write-set compliance, and review pass with evidence.

Before implementation and after material changes, verify:

- System PRD goals, non-goals, requirements, scenarios, and success criteria agree with the canonical register.
- Each component PRD's owned requirement IDs are consistent with `TRACEABILITY.md`'s `Primary component` column, with no ID owned by two components.
- Each PLAN (System or component) derives from its current PRD, covers every in-scope requirement, respects constraints, and defines verification/recovery.
- Every task is justified by a requirement, foundation, or verification need; dependencies are complete and acyclic; `gates:` entries resolve; parallel labels match write sets.
- Every mandatory requirement maps to design, tasks, and verification or an explicit `gates:` blocker.
- Actual repository state matches reported task state.
- Local links resolve and no repository instruction depends on a path above the repository root.
- Do not prematurely author component PLAN internal detail for a component whose owning task has not started (see the shallow-PLAN pattern in `planning/COMPONENTS.md`); do not micro-plan stale future detail.

## 11. Prohibited workflow patterns

Do not duplicate requirements across artifacts, maintain competing status ledgers, create vague mega-tasks, code before required approval, micro-plan stale future details, run false parallel work, share mutable state without isolation, expand scope silently, guess missing requirements, mark unverified work done, hide failure, retry without bounds, keep decisions only in conversation memory, or model a criterion-scoped ambiguity as a whole-task `depends_on` edge when a `gates:` entry with `blocks: criterion` or `blocks: integration` is the honest representation.

## 12. Bundle/submodule-aware synchronization

Where the general planning repository packages multiple repositories via Git submodules:

- Bundle-level files under `requirements/` and `planning/` are **package masters**.
- Each role repository's `docs/spec/`, `docs/inputs/`, `docs/components/`, `docs/mechanisms/`, and `docs/contracts/` contain **synchronized repository-local execution copies**, so the repository remains usable when cloned alone.
- Role-specific content (component/mechanism PLANs, role-specific mechanism PRDs, ADRs, tasks, TODO) is **role-owned**; the bundle reads it through the pinned submodule commit and never keeps a second raw copy.
- Repository workers use only paths inside their own repository; the package orchestrator is the only actor that synchronizes master and execution copies, and it does so only after the reviewed child-repository commits exist.
- A submodule gitlink is updated only to a specific reviewed commit (normal pinned-commit semantics); submodules are not converted into copied directories and are not configured to permanently track a temporary planning branch without an already-approved repository policy.

## 13. Final operating questions

Before implementation, every worker must be able to answer:

1. Which approved requirement is implemented, and which component primarily owns it?
2. Which PLAN decision (System or component) governs the approach?
3. Which task, `write_set`, and `read_set` are exclusively/additionally owned?
4. Which `depends_on` dependencies are satisfied and which `gates:` entries, if any, still block `start`?
5. Why is parallel execution safe or unsafe?
6. How will completion be verified, including any `criterion`/`integration` gates the acceptance criteria name?
7. What evidence must the handoff contain?
8. What happens if a requirement, architecture, input, or scope conflict is found?

If an answer is materially unclear, stop and clarify before implementation.
