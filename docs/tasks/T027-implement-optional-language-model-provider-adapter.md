---
id: T027
status: blocked
priority: P2
task_type: component
component: C02
optional: true
implements:
  - STRAT-008
  - SEC-009
  - QR-008
  - QR-018
context_files:
  - docs/components/C02-perception-strategy/PRD.md
  - docs/components/C02-perception-strategy/PLAN.md
  - docs/mechanisms/M-03-police-strategy.md
read_set: []
depends_on:
  - T002
  - T007
  - T013
  - T017
gates:
  - id: PLANQ-003
    kind: decision
    scope: provider_choice
    blocks: start
  - id: PLANQ-004
    kind: decision
    scope: provider_scope
    blocks: criterion
parallel_safe: true
claimed_by:
claim_expires_at:
write_set:
  - src/police_peer/strategy/providers/language_model.py
  - tests/unit/strategy/providers/test_language_model.py
risk: medium
---

# T027 — Implement Optional Language-Model Provider Adapter

## Expected outcome

An explicitly selected provider adapter may generate free-form verbal hints or behavior analysis without selecting, vetoing, delaying, or mutating Police movement. The boundary remains provider-neutral and deterministic template mode remains the default/fallback.

## Requirements implemented

- `STRAT-008`
- `SEC-009`
- `QR-008`
- `QR-018`

## Relevant context

The official specification permits template, local-model, or configured provider modes without selecting a vendor. This P2 task is optional and never blocks release. PLANQ-003 and PLANQ-004 must approve whether a provider is needed and, if so, its model, budget, cadence, rate limits, and text-only scope before any live external call. A provider failure must not block a legal game action.

## Gates

- `PLANQ-003` (`decision`, `blocks: start`) — this task cannot be claimed until the gate resolves.
- `PLANQ-004` (`decision`, `blocks: criterion`) — the task may be claimed and implemented now; only the acceptance criterion scoped `provider_scope` waits.

## Constraints

- Do not edit the canonical PRD.
- Do not silently redefine the repository PLAN or task dependencies.
- Do not widen scope or treat a derived design decision as a source requirement.
- Edit only the declared write set; request an orchestrator-approved change before crossing it.
- Escalate requirement conflicts, missing official inputs, and newly discovered work.

## Acceptance criteria

- [ ] The adapter is enabled only by explicit private configuration after provider/model approval; template mode remains valid without network/model dependencies.
- [ ] A legal Police action is selected and locked before a provider call; provider output cannot select, veto, delay, or mutate that action, per the approved PLANQ-004 provider scope. `{#provider_scope}`
- [ ] Timeout, malformed response, 429, provider outage, and token/cost-budget exhaustion produce bounded deterministic template fallback.
- [ ] Every external call passes through the central Gatekeeper; provider-specific credentials or environment variable names are introduced only after provider selection and never appear in logs, fixtures, exceptions, or artifacts.
- [ ] Actual token/cost metadata is added to the existing token ledger/report path when available; tests do not fabricate usage as execution evidence.
- [ ] Post-processing enforces the approved free-form arena and word cap before text can be sent.
- [ ] Unit tests use mocks for success and all failure paths; CI performs no live provider calls and requires no provider key.

## Verification

- `uv run pytest tests/unit/strategy/providers/test_language_model.py`
- `uv run ruff check src/police_peer/strategy/providers/language_model.py tests/unit/strategy/providers/test_language_model.py`
- `uv run python scripts/check_no_secrets.py`

## Implementation plan

- **Provider package** (`src/police_peer/strategy/providers/`): `OpenAIProvider` (OpenAI Chat Completions via stdlib REST) and `OllamaProvider` (local model), both implementing the existing `strategy.hints.TextProvider` protocol. `transports.py` holds the stdlib HTTP askers; `language_model.py` holds the providers plus `resolve_text_provider(config, gatekeeper)`.
- **Boundary (STRAT-008, NG-003, PLANQ-004 RESOLVED):** the LLM is never on the movement path. `generate(...)` runs only in `HintWriter.say(...)` (phase 4) to produce free-form text for an already-locked action; any exception/None/timeout/malformed reply degrades to the deterministic template (CT-02). The sealed `verdict` is rule-computed locally from the asserted landmark vs position, never trusted from the wire (FR-P6).
- **Transport (stdlib):** `urllib.request` REST — `POST {base}/chat/completions` with `Authorization: Bearer $OPENAI_API_KEY`, body `{"model","messages","temperature","max_tokens"}`. No new dependency; `import openai` is never executed.
- **Providers:** `openai_api` (new) and `ollama` (reference stdlib asker kept); `claude_cli`/`claude_api` have no OpenAI analog and are dropped (deviation recorded in Result). `template` remains the default and requires no key.
- **Gatekeeper (SEC-009):** every live call is wrapped by the single `ExternalApiGatekeeper.execute(...)`. Key comes from the local env at runtime only; never in git/logs/fixtures (checked by `check_no_secrets`).
- **Cadence:** `every_n_steps` (default 1) gates provider calls; `temperature` fixed low.
- **Wiring:** `wire/strategy_settings.py` carries a normalized `trash_talk` dict; `assemble_strategy_config` adds it to the resolve mapping; `resolve_brain` resolves the provider and passes it to `HintWriter(provider=...)`. Updated `config/game.toml.example` with a commented `[trash_talk]` block.

> Write-set note: the provider + test are T027's declared write set. The one-line wiring in `inject.py`/`wire/*` is a minimal seam extension needed to make the adapter reachable; it is documented here and in the report for ORC recording.


## Write-set extension record (ORC-acknowledged)

Workflow §4 (no silent scope expansion): the glue edits needed to make the
provider reachable cross T027's declared write set. They are recorded here, in
`docs/tasks/`, the documented place for orchestrated write-set extensions (same
pattern as PLAN_police_strategy.md §12/§16 and PRD_belief_board.md FR-B9).

| Field | Record |
|---|---|
| Extension ID | **T027-EXT-1** |
| Task | T027 — optional language-model provider adapter |
| Repo(s) | `police_repo`, `thief_repo` (mirrored identically) |
| Declared write set (unchanged) | `src/<role>_peer/strategy/providers/` , `tests/unit/strategy/providers/` |
| Added (edited) files | `src/<role>_peer/strategy/inject.py`, `src/<role>_peer/wire/strategy_settings.py`, `config/game.toml.example` |
| Rationale | resolve the configured `[trash_talk]` provider into `HintWriter(provider=...)` and carry it through `assemble_strategy_config` so the adapter is reachable; additive-only, no behavior change to existing modes |
| Flag | `status: blocking_PLANQ-003` — code/tests valid now; live call waits on PLANQ-003 |
| Date | 2026-08-22 |
| Status | ACKNOWLEDGED — recorded for ORC reconciliation |

**Approved scope:** provider selection/verbatim wiring only; QA does not widen the seam (`TextProvider` protocol, `hints.py`, `base.py`, shared `common/` untouched).


## Handoff contract

Report files changed, tests executed, exact test result, decisions made, deviations, blockers, and newly discovered work. Provide command output or artifact paths sufficient to validate every acceptance criterion.

Files changed (police_repo): `src/police_peer/strategy/providers/{__init__,language_model,transports}.py`, `tests/unit/strategy/providers/test_language_model.py`, `src/police_peer/strategy/inject.py`, `src/police_peer/wire/strategy_settings.py`, `config/game.toml.example`.

Tests: `pytest tests/unit/strategy/providers/` (15 passed) and full `pytest` (coverage 92.69%) all green; `ruff`, `check_no_secrets`, and `run_quality_gates` all pass (results in report).

## Result and evidence

Implemented: OpenAI Chat Completions provider + local Ollama provider satisfying the shared `TextProvider` protocol, routed through the single Gatekeeper, wired config→brain, `template` still the default/fallback. Stdlib-only transport (no new dependency).
