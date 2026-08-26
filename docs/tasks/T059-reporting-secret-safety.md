---
artifact: task
id: T059
title: Harden reporting secrets and live-send authorization
status: done
priority: P0
task_type: component
optional: false
owner: orchestrator
component: C06
depends_on: [T017, T018, T058]
context_files:
  - docs/components/C06-reporting-league/PRD.md
  - docs/components/C06-reporting-league/PLAN.md
gates: []
claimed_by: root-codex
claim_expires_at: 2026-08-27T15:57:46Z
write_set:
  - .env.example
  - .gitignore
  - config/game.toml.example
  - config/repo_quality.toml
  - docs/GMAIL_API.md
  - docs/tasks/T059-reporting-secret-safety.md
  - scripts/send_kit_email.py
  - src/police_peer/infra/gmail_oauth.py
  - src/police_peer/wire/gmail_composition.py
  - src/police_peer/wire/identity_config.py
  - tests/integration/test_gmail_production_composition.py
  - tests/helpers.py
  - tests/test_repository_safety.py
  - tests/unit/infra/test_gmail_oauth.py
  - tests/unit/test_private_config_identity.py
---

# T059 — Reporting secret and live-send safety

## Goal

Align the production reporting boundary with the local official v3.0.0 book and the
machine-secret policy: use the official recipient, reuse explicit external OAuth file paths,
verify the stored token's exact send-only scope, prevent helper scripts from bypassing the
Gatekeeper, and protect variant credential/token filenames.

## Acceptance criteria

- [x] The official recipient is `rmisegal+uoh26finalgame@gmail.com`; dry-run remains the default.
- [x] Live delivery remains limited to counted execution plus explicit human authorization.
- [x] The standalone helper cannot directly construct Google clients or bypass the Gatekeeper.
- [x] Stored OAuth metadata is rejected unless its scope is exactly `gmail.send`.
- [x] OAuth files are resolved through `GMAIL_OAUTH_CLIENT_FILE` and
      `GMAIL_OAUTH_TOKEN_FILE`; no secret is copied into the repository.
- [x] Variant credential/token JSON names are ignored and rejected by repository safety gates.
- [x] Tests use fakes and make no live OpenRouter or Gmail call.

## Verification

- `uv run pytest tests/unit/infra/test_gmail_oauth.py tests/integration/test_gmail_production_composition.py tests/test_repository_safety.py`
- `uv run ruff check .`
- `uv run python scripts/check_no_secrets.py`
- `uv run python scripts/run_quality_gates.py`

## Result and evidence

- Full `uv run pytest -q`: passed at 87.84% coverage. One existing Python 3.14 event-loop deallocator warning was emitted.
- Full `uv run ruff check .`: passed.
- `scripts/run_quality_gates.py`: all seven generic repository gates passed.
- Deterministic two-peer smoke: `verified_ok`; the kit contains exactly 14 JSON files
  (1 declaration, 6 configs, 6 logs, 1 result) with one consistent `game_id` and `game_uid`.
- Template token evidence contains only known numeric zeroes.
- Protected local Gmail paths composed successfully and the stored token scope validated without
  constructing a Gmail client or sending a message.
- No Gmail or OpenRouter network call was made.
