# Contributing

## Before work starts

1. Select a `ready` row in `docs/TODO.md` whose dependencies are satisfied.
2. Atomically set `claimed_by` and `claim_expires_at` in the task file and ask the orchestrator to mirror the claim in TODO.
3. Confirm that no active task overlaps the proposed `write_set`.
4. Create a separate branch/worktree named `task/T###-short-slug`.
5. Complete the task's low-level Implementation plan immediately before coding.

The Markdown task file owns execution scope and evidence. A GitHub Issue may discuss it and a Pull Request may deliver it, but neither replaces the task ID, dependencies, status, or write set. Resolve requirement and OPEN IDs from `docs/spec/`, and authoritative input status from `docs/inputs/INPUT_REGISTER.md`; no task requires a path outside this repository.

## Branches, issues, commits, and Pull Requests

- Branch: `task/T###-short-slug`; use `fix/T###-short-slug` only for a defect inside an approved task.
- Issue title: `T###: concise outcome`; link the task file and record no alternative execution state.
- Commit subject: `T###: imperative summary`. Keep commits reviewable and never include secrets or generated credentials.
- Pull Request: one task where practical; list requirement IDs, files changed, acceptance evidence, exact commands/results, decisions, deviations, blockers, and follow-up task proposals.
- Review: at least one teammate reviews behavior, tests, secrets, documentation, and write-set compliance. Integrity/reporting/release tasks also require orchestrator review.

## Ownership and scope

- Only the orchestrator edits the canonical PRD, repository PLAN, task dependencies, or global ledger structure.
- A worker edits only the claimed task's write set and never widens project scope.
- A conflict with requirements or missing official input stops the task; record a blocker instead of guessing.
- New work receives a new task ID from the orchestrator. Do not hide it inside the current PR.
- Prefer separate branches/worktrees for parallel work. Parallel tasks must have non-overlapping write sets.
- Begin from official requirement IDs and the claimed task. Project engineering evidence may inform tests after scope is fixed, but it cannot settle an official ambiguity or redefine the product contract.
- Do not add third-party code or configuration without orchestrator approval, verification of license obligations, and preservation of every legally required notice.

## Quality gates

After dependency lock approval, run:

```sh
uv sync --locked --all-groups
uv run ruff check .
uv run pytest
uv run python scripts/run_quality_gates.py
```

Use `uv` only. Do not add `requirements.txt`, direct `pip` instructions, or a second dependency source. Tests do not contact live MCP peers, Gmail, tunnels, or paid model services; use deterministic fakes/mocks until the relevant human gate.

## Documentation and secrets

- Update documentation when public behavior/configuration changes, but do not edit PRD/PLAN unless acting as orchestrator under approved change control.
- Never commit `.env`, `credentials.json`, `token.json`, passwords, access tokens, private keys, national identifiers, or private personal data.
- Examples contain placeholders only. Screenshots, metrics, test results, strategies, and league outcomes must be real, traceable evidence.
- An arriving official input is registered and verified, then affected OPEN items and derived artifacts are updated; input receipt alone does not create a Change Request.
- A sufficiently important durable technical decision may use an ADR and does not change product scope.
- A material requirement or PRD-contract change needs a Change Request with affected IDs, source/authority, motivation, impact, approval, resulting PRD version, and synchronized PLAN/task updates.
- Additional implementation work receives a new task ID instead of a Change Request or silent expansion of the current task.

## Definition of Done

A task is done only when:

- every dependency was complete before implementation;
- every acceptance checkbox is satisfied;
- every listed verification command passes with exact results recorded;
- code meets Ruff zero, 85% global coverage, and the configured 150-line threshold;
- write-set and no-secret checks pass;
- required docs/evidence are updated truthfully;
- review is complete and the structured handoff is validated;
- the orchestrator reconciles the PLAN/TODO/task graph and marks the task done.

Merge only after all required checks and reviews pass. Use the repository's normal reviewed merge policy; do not bypass protected checks or rewrite shared history.
