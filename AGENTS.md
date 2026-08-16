# AGENTS.md

## Repository purpose

This repository is the autonomous Police peer of a two-process P2P hidden-state game. It must own only local truth, expose/call FastMCP tools, maintain belief and strategy, protect each step with Commit-Reveal, show a local Live GUI/Replay, and produce compliant signed reporting artifacts.

## Source-of-truth hierarchy

1. Official project specification for project behavior/submission.
2. Official software-quality guide for classified quality expectations.
3. Repository-local `docs/spec/CANONICAL_REQUIREMENTS.md`, `docs/spec/OPEN_QUESTIONS.md`, `docs/spec/TRACEABILITY.md`, `docs/spec/PRD_PLAN_TODO_AGENT_WORKFLOW.md`, `docs/inputs/INPUT_REGISTER.md`, and `docs/PRD.md` for approved intent, workflow, and unresolved inputs.
4. `docs/PLAN.md` for repository system-level technical strategy; `docs/components/*/PRD.md` and `docs/components/*/PLAN.md` for one component's contract and design; `docs/mechanisms/*.md` for a dedicated algorithm; `docs/contracts/*.md` for a cross-component boundary.
5. `docs/TODO.md` plus `docs/tasks/T###-*.md` for execution scope/state/evidence.

Stop and escalate contradictions. Never convert an example, recommendation, default, or derived design into a mandatory requirement.

In the packaged bundle, the files under `requirements/` and `planning/` are package masters and the files under `docs/spec/`, `docs/inputs/`, `docs/components/*/PRD.md`, `docs/mechanisms/` (shared ones), and `docs/contracts/` are synchronized repository-local execution copies. When this repository is used alone, resolve every requirement, OPEN item, traceability entry, and input record from the local copies; never require a path above the repository root.

## Bounded task context (read this before claiming any task)

A normal worker (human or agent) reads, in order: this file, the claimed task's own file, every path listed in that task's `context_files` frontmatter field, the requirement/OPEN/input/decision IDs the task names, and any path listed in its `read_set` (additional read-only scope outside the task's own `write_set` — every path already in `write_set` is always readable and writable by the claiming worker). This is normally a handful of files, not the whole repository.

Do **not** default to reading the entire System PRD, System PLAN, canonical register, and task graph for a `component`-typed task — its `context_files` already names the one component PRD/PLAN (and, where declared, one mechanism PRD or contract) that fully specifies its scope. Reading more than the declared bounded context is a sign the task's `context_files` is incomplete, not a routine step — report it as a task-definition defect rather than silently over-reading.

Wider context is expected only for `governance` and `release`-typed tasks, whose `context_files` may legitimately include the System PRD/PLAN.

A task's `gates:` list distinguishes three levels: `blocks: start` (the task cannot be claimed), `blocks: criterion` (the task proceeds; only the named acceptance criterion waits), and `blocks: integration` (the task completes locally; it cannot pass the named integration gate in the project-level integration plan yet). Check `blocks: start` gates before claiming; the other two are checked when you reach the criterion or integration gate they name.

## Architecture map

- Domain: board, local state, movement, barriers, capture, scoring.
- Scent/belief: deterministic scent model and local opponent probability.
- Strategy: Police-specific decisions; verbal text providers are isolated from movement selection.
- Orchestration/reliability: legal state transitions, deadlines, retry, watchdog/recovery.
- Transport/integrity: FastMCP server/client, negotiated contracts, Commit-Reveal/audit.
- Reporting/infrastructure: official artifacts and one external-service Gatekeeper for Gmail and any approved optional model provider.
- UI: local-truth Live GUI and immutable verified Replay.
- `sdk.py`: thin programmatic entry; GUI/CLI/MCP stay adapters.

The tree in PLAN is proposed. Create only paths owned by the active task.

## Commands

When the approved lock is present:

```sh
uv sync --locked --all-groups
uv run ruff check .
uv run pytest
uv run python scripts/run_quality_gates.py
```

When the approved lock is absent, use `uv sync --all-groups` only for infrastructure validation and do not commit a provisional lock as a release dependency baseline.

## Coding conventions

- Python 3.12 baseline until T002 approves otherwise; type public boundaries.
- Pure deterministic domain functions; inject clocks, randomness, filesystem, network, and external services.
- Prefer a plain function for stateless behavior; use a class only when it owns state, invariants, or lifecycle.
- Compose dependencies manually through narrow `Protocol`/`Callable` seams; do not add a DI container, generic Repository/Unit of Work, domain-event bus, or CQRS without a concrete need and approved PLAN/ADR change.
- Make mutable-state ownership explicit; bound concurrent work with timeouts, cancellation, and cleanup, and keep blocking I/O outside the event loop.
- Descriptive names, narrow modules/functions, decision-oriented docstrings, no speculative inheritance/plugins/services.
- No code file over 150 nonblank, noncomment lines; do not compress code to pass.
- One canonical integrity path and one external-service Gatekeeper.
- Configuration owns adjustable values; shared JSON overrides conflicting private TOML.
- Never expose objective opponent state to strategy inputs, logs, or Live GUI.

## PRD, PLAN, TODO, and claiming

- Only the orchestrator edits a PRD (System or component), a PLAN (System or component), task dependencies/gates, or global TODO structure.
- A worker may update claim/result fields only in the claimed task and may request the orchestrator to mirror ledger state.
- Claim before implementation: set `claimed_by`, set a finite `claim_expires_at`, and verify dependencies/status/write-set exclusivity. A task is `ready` only when every `depends_on` task is `done` and no `gates:` entry has `blocks: start`.
- Use a separate `task/T###-slug` branch/worktree where practical.
- Edit only the declared write set. Ask before crossing it.
- Newly discovered work gets a new task; scope never expands silently.
- Record and verify an arriving official input in `docs/inputs/INPUT_REGISTER.md`, then update affected OPEN items and derived artifacts. Do not open a Change Request unless approved requirement or PRD meaning changes.
- Use an ADR only for a sufficiently important durable technical decision. A Change Request is only for a material approved product/requirement change and must name affected IDs, source/authority, impact, approval, and resulting PRD version.

## Verification and handoff

Run every task-specific command plus the repository gates. A handoff reports files changed, tests executed, exact results, decisions, deviations, blockers, and newly discovered work. The orchestrator validates evidence before changing status to done and reconciles the graph after every wave.

## Prohibited operations

- No shared live memory/module with the sibling peer and no central judge.
- No direct numeric-position replacement for the natural-language channel.
- No guessed official JSON/Word schema, hidden barrier, fabricated evidence, or silent sanction choice.
- Do not add third-party code or configuration without orchestrator approval, verification of license obligations, and preservation of required notices.
- No direct Gmail/model API call outside Gatekeeper and no live external call in tests.
- No secrets, private IDs, credentials, tokens, keys, or passwords in Git/logs/examples.
- No `requirements.txt`, direct `pip`, destructive Git history rewrite, bypassed checks, or unapproved PRD/PLAN/dependency change.

## Repository Definition of Done

The repository is releasable only when all P0/P1 tasks and human gates are complete; all MUST requirements have evidence; open blockers are resolved; PRD/PLAN/TODO/task graph agree; Ruff, pytest/85% coverage, line cap, secret/docs/link/task/archive/workflow checks pass; two-process interoperability and recovery pass; real GUI/Replay evidence exists; signed reports reconcile; and the exact reviewed commit is tagged `v1.0-submission` and made accessible as required.
