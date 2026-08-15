# PRD / PLAN / TODO Agent Workflow

> Repository execution copy of the approved planning methodology. This file contains the repository-facing rules needed for standalone work and preserves the methodology's artifact ownership, stable-ID, change-control, task, orchestration, and verification semantics.

## 1. Artifact ownership

| Artifact | Owns | Must not become |
|---|---|---|
| `PRD.md` | Product intent, actors, goals, scope, requirements, success criteria, constraints, assumptions, risks, open questions, approval history | Architecture detail or live task state |
| `PLAN.md` | Architecture, boundaries, interfaces, technical strategy, decisions, execution waves, requirement coverage, validation, recovery, and gates | A duplicate PRD or status board |
| `TODO.md` | Compact execution index and progress overview | A second detailed task store |
| `tasks/T###-*.md` | Atomic scope, requirements, dependencies, claim, write set, acceptance, verification, plan, handoff, and evidence | A place to invent product requirements |
| `AGENTS.md` | Stable repository rules, commands, permissions, and conventions | Feature-specific scope or task state |
| ADR | A sufficiently important and durable technical decision | Product scope, input receipt, or task state |
| Change Request | A proposed material change to an approved requirement or PRD contract | Input intake, technical choice, or implementation backlog |
| Code and tests | Actual implemented behavior and verification | The sole statement of intended behavior |

Changes flow from PRD to PLAN to TODO/tasks to implementation to evidence. A downstream artifact must not silently redefine an upstream artifact.

## 2. Stable identifiers and traceability

- Requirements, OPEN items, tasks, ADRs, and Change Requests use stable published IDs.
- Never renumber later IDs to close a gap.
- Tasks and PLAN elements reference canonical requirement IDs instead of copying large requirement prose.
- Traceability flows from requirement to PLAN design to tasks to verification evidence.
- Removed work keeps its historical ID when history matters; dangling dependencies and links are prohibited.

## 3. Lifecycle and approval gates

The normal lifecycle is discover, specify, clarify, approve PRD, plan, review PLAN, decompose, validate consistency, execute dependency waves, reconcile each wave, verify, and close.

- Do not skip an explicit human or automated gate merely because work can continue technically.
- Only the orchestrator edits PRD, PLAN, task dependencies, or global TODO structure.
- Workers update only authorized claim/result fields and their declared write sets.
- Approved requirement meaning never changes silently during implementation.

## 4. Event semantics

### Official input arrives

1. Record it in `docs/inputs/INPUT_REGISTER.md` without secret contents.
2. Verify authority, completeness, version, and any safe hash.
3. Update affected `OPEN-*` entries.
4. Reconcile derived PLAN, tasks, tests, and traceability when needed.
5. Open a Change Request only if accepting the information materially changes an already-approved canonical product requirement or PRD contract.

### Technical design decision

Use an ADR only when the decision is important and durable enough to preserve. An ADR does not change product scope.

### Product or requirement change

A Change Request is required when a requirement is added, removed, or normatively changed, a binding constraint changes, or the approved PRD contract changes materially. It names affected requirement IDs, motivation, source/authority, impact, approval, and resulting PRD version. After approval, synchronize the canonical register if authorized, both PRDs, PLAN coverage, tasks, tests, and traceability.

### Additional implementation work

Create a new stable task ID. Do not open a Change Request and do not silently expand the active task when product scope is unchanged.

## 5. Task model

Recommended states are `backlog`, `ready`, `claimed`, `in_progress`, `review`, and `done`; exceptional states are `blocked`, `failed`, `cancelled`, and `superseded`.

- `ready` means every known prerequisite is represented and satisfied.
- `blocked` names the concrete dependency or decision required.
- `done` requires accepted criteria and recorded verification evidence.
- A task has one clear outcome, stable ID, requirement references, dependencies, finite claim, write set, acceptance criteria, verification, just-in-time implementation plan, and handoff contract.
- A task is small enough for one focused worker context and one reviewable change.
- Newly discovered work is reported to the orchestrator for a new task ID.

## 6. Claiming and execution

Before implementation, a worker must:

1. read `AGENTS.md`, the task, referenced requirement and OPEN IDs, and relevant PLAN sections;
2. verify dependencies and status;
3. claim the task with claimant and finite expiry;
4. confirm exclusive, non-overlapping write ownership;
5. write a short implementation plan against current repository state;
6. edit only the declared write set;
7. run focused verification and repository gates;
8. return files changed, exact commands/results, acceptance evidence, decisions, deviations, blockers, and proposed follow-up tasks.

The orchestrator validates the handoff against repository state before changing task status.

## 7. Parallel execution

Tasks may run in parallel only when dependencies are satisfied, they do not need one another's intermediate state, write sets do not overlap, shared external resources have a concurrency protocol, claims are exclusive, integration order is known, and one failure cannot make the other task unsafe.

Before each wave, verify readiness and write sets. After each wave, validate results, integrate deterministically, run wave-level tests, reconcile PLAN/TODO/tasks/traceability, and stop on blocking failure.

## 8. Safety and permissions

- Apply least privilege and preserve unrelated work.
- Never place credentials, tokens, keys, passwords, private IDs, or secret contents in planning artifacts, code, tests, examples, logs, or the Input Register.
- Destructive, release, public-network, live-email, and submission actions require their stated human gates.
- Report permission failures and blockers; do not bypass controls.
- Do not add third-party code or configuration without verifying license obligations and preserving required notices.

## 9. Verification and consistency

A task is complete only when acceptance criteria, focused tests, required static/build checks, documentation, write-set compliance, and review pass with evidence.

Before implementation and after material changes, verify:

- PRD goals, non-goals, requirements, scenarios, and success criteria agree.
- PLAN derives from the current PRD, covers every in-scope requirement, respects constraints, and defines verification/recovery.
- Every task is justified by a requirement, foundation, or verification need; dependencies are complete and acyclic; parallel labels match write sets.
- Every mandatory requirement maps to design, tasks, and verification or an explicit blocker.
- Actual repository state matches reported task state.
- Local links resolve and no repository instruction depends on a path above the repository root.

## 10. Prohibited workflow patterns

Do not duplicate requirements across artifacts, maintain competing status ledgers, create vague mega-tasks, code before required approval, micro-plan stale future details, run false parallel work, share mutable state without isolation, expand scope silently, guess missing requirements, mark unverified work done, hide failure, retry without bounds, or keep decisions only in conversation memory.

## 11. Final operating questions

Before implementation, every worker must be able to answer:

1. Which approved requirement is implemented?
2. Which PLAN decision governs the approach?
3. Which task and write set are exclusively owned?
4. Which dependencies and gates are satisfied?
5. Why is parallel execution safe or unsafe?
6. How will completion be verified?
7. What evidence must the handoff contain?
8. What happens if a requirement, architecture, input, or scope conflict is found?

If an answer is materially unclear, stop and clarify before implementation.
