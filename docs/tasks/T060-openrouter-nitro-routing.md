---
artifact: task
id: T060
title: Configure unpinned OpenRouter Nitro routing
status: done
priority: P0
task_type: component
optional: false
owner: orchestrator
component: C06
depends_on: [T050, T051]
context_files:
  - docs/PRD_llm_provider.md
  - docs/PLAN_llm_provider.md
gates: []
claimed_by: root-codex
claim_expires_at: 2026-08-27T16:16:28Z
write_set:
  - .env.example
  - config/game.toml.example
  - config/private/llm-openrouter.toml
  - docs/OPENROUTER.md
  - docs/spec/OPEN_QUESTIONS.md
  - docs/tasks/T060-openrouter-nitro-routing.md
  - src/police_peer/infra/openrouter_client.py
  - src/police_peer/wire/identity_config.py
  - tests/contract/test_openrouter_client.py
  - tests/integration/test_llm_production.py
  - tests/live/test_openrouter_smoke.py
  - tests/unit/wire/test_llm_config.py
---

# T060 — OpenRouter Nitro routing

## Goal

Use `deepseek/deepseek-v4-flash-0731:nitro` for real-game OpenRouter wording without
pinning a provider, while retaining the existing explicit-provider routing option and the
deterministic template fallback.

## Acceptance criteria

- [x] The real-game example and private profile select the Nitro model with no provider slug.
- [x] An unpinned client omits the OpenRouter provider routing block.
- [x] An explicitly configured provider slug still sends the pinned routing block.
- [x] Provider failures still preserve deterministic gameplay through template fallback.
- [x] Tests use in-memory transports and make no live OpenRouter call.

## Verification

- `uv run pytest --no-cov tests/contract/test_openrouter_client.py tests/unit/wire/test_llm_config.py tests/unit/strategy/test_hints.py tests/integration/test_llm_production.py`
- `uv run ruff check .`

## Result and evidence

- The focused offline suite passed all 50 tests.
- Full-repository Ruff passed.
- All seven generic repository quality gates passed.
- The Police full offline suite also passed without coverage instrumentation.
- No live OpenRouter or Gmail request was made.
