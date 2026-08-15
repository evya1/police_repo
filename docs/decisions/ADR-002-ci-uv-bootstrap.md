---
artifact: adr
id: ADR-002
status: accepted
date: 2026-08-15
owners: orchestrator
related_requirements: [QR-011, QR-014, QR-015, SEC-010]
related_tasks: [T002, T024]
supersedes:
---

# ADR-002 — CI bootstraps uv from a pinned, checksum-verified release

Use an ADR only for a sufficiently important and durable technical design decision. Official-input receipt belongs in the Input Register, product/requirement changes belong in a Change Request, and execution work belongs in a task.

## Context

`QR-014` requires `uv` as the package manager and task runner, so continuous integration must obtain `uv` before it can run any repository command. The scaffold's original workflow obtained it from the third-party marketplace action `astral-sh/setup-uv`, pinned to `@v10`.

That pin never resolved. The action publishes floating major aliases for `v1` through `v7` only; from `v8` onward it publishes full semantic-version tags exclusively, so `v8`, `v9`, and `v10` exist as `v8.3.2`, `v9.0.0`, `v10.0.1` and so on, with no floating alias. Every workflow run therefore failed during action resolution, before checkout completed and before any repository command executed. This blocked all pull requests regardless of their content.

Two constraints shape the replacement. First, `AGENTS.md`, `CONTRIBUTING.md`, and `docs/spec/PRD_PLAN_TODO_AGENT_WORKFLOW.md` each require that third-party code or configuration is not adopted without orchestrator approval and verified license obligations; a marketplace action is exactly such a dependency, and re-pinning it renews that dependency rather than resolving it. Second, `CONTRIBUTING.md` requires `uv` only, with no `requirements.txt`, no direct `pip` instructions, and no second dependency source, which rules out installing `uv` through `pip` or `pipx`.

The repository's own workflow gate (`scripts/check_workflow_permissions.py`) constrains only the top-level `permissions` mapping and forbids every `write` scope while `workflow_allowed_write_permissions` is empty. It does not inspect `uses:` or action versions, so the choice of bootstrap mechanism is unconstrained by the gate and is governed by this decision instead.

## Decision

Continuous integration installs `uv` directly from its official GitHub release, verified against a digest recorded in the workflow, and uses no marketplace action for that purpose.

The workflow pins two values as top-level `env` entries: `UV_VERSION`, the exact release tag, and `UV_SHA256`, the SHA-256 of that release's `uv-x86_64-unknown-linux-gnu.tar.gz` asset. The install step downloads only the tarball, verifies it against the pinned digest, extracts `uv` and `uvx` into `${HOME}/.local/bin`, and appends that directory to `${GITHUB_PATH}`. A mismatch fails the job.

The digest is recorded here rather than fetched next to the download. Retrieving a checksum from the same origin as the artifact it describes proves only that the transfer was not corrupted; it cannot detect a release whose contents changed after review, because whoever could alter the artifact could alter the accompanying checksum. Pinning the digest in version control makes the bootstrap reproducible and any change to the upstream artifact visible as a failing job rather than a silent substitution.

`actions/checkout` is retained. It is maintained by GitHub as first-party infrastructure, its `v6` floating tag resolves, and replacing it with a manual clone would add credential handling for no security benefit.

Both repositories keep byte-identical workflow files, and the three command groups — Ruff, pytest, and the repository quality gates — remain unchanged and continue to mirror `.pre-commit-config.yaml`.

## Alternatives considered

- **Re-pin the action to `astral-sh/setup-uv@v10.0.1`.** The smallest possible change and it would work. Rejected because it preserves a third-party dependency that the repository's own governance requires justifying, and it leaves the same failure mode: the next major release drops the alias again and CI breaks a second time for the same reason.
- **Pin the action to `@v7`, the last floating alias.** Resolves today, but deliberately freezes on an old major version and still carries the third-party dependency.
- **`pip install uv` or `pipx install uv`.** One line each, and `pipx` is preinstalled on the runner. Rejected because `CONTRIBUTING.md` forbids direct `pip` instructions and a second dependency source, and neither gives a digest we control.
- **The official installer script, `curl -LsSf https://astral.sh/uv/install.sh | sh`.** Astral's documented path and version-pinnable through `UV_VERSION`. Rejected because it executes a remote script fetched at run time, which is a strictly larger trusted surface than downloading one archive and checking it against a known digest.
- **Drop `uv` from CI and use the preinstalled Python 3.12 with `pip`.** The runner image already ships the required interpreter, and the gate scripts are nearly pure standard library. Rejected because `QR-014` makes `uv` the mandated package manager and task runner, and CI must exercise the same path contributors use.

## Consequences

Positive: CI no longer depends on any third-party marketplace action; the toolchain is reproducible because a given commit always installs one specific verified binary; a compromised or altered upstream artifact fails the job instead of executing; and the bootstrap is auditable from the workflow file alone, which serves the `QR-015` review expectation.

Negative: upgrading `uv` now requires editing two pinned values instead of relying on a floating tag, and the digest is architecture-specific, so moving to ARM runners would require a matching asset and digest. The action's dependency caching is also lost; on this repository that costs a single archive download per run and is not material.

Interoperability and migration: no repository command changed, so local, pre-commit, and CI behaviour remain identical. `T002` owns `.github/workflows/ci.yml` and inherits this decision; when it commits the approved `uv.lock` it should change `uv sync --all-groups` to `uv sync --locked --all-groups` and leave the bootstrap intact.

Security: the workflow keeps `permissions: contents: read` with no write scope, and the bootstrap introduces no secret, token, or credential.

## Validation

- `scripts/check_workflow_permissions.py` passes, confirming the top-level `permissions` mapping still declares no `write` scope.
- The full gate suite (`scripts/run_quality_gates.py`), `ruff check .`, and `pytest` pass unchanged in both repositories.
- The install sequence was executed end-to-end before adoption: the pinned digest verified against the real published asset, extraction produced a working binary reporting `uv 0.12.5`, and a deliberately incorrect digest was confirmed to fail the check rather than proceed.
- A CI run on the pull request demonstrates the workflow resolving and completing, which the previous configuration could not do.

## Approval

- Decision owner: orchestrator
- Approved by: project team
- Approval date: 2026-08-15
