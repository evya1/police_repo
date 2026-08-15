---
id: T027
status: blocked
priority: P2
implements:
  - STRAT-008
  - SEC-009
  - QR-008
  - QR-018
depends_on:
  - T002
  - T007
  - T013
  - T017
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

## Constraints

- Do not edit the canonical PRD.
- Do not silently redefine the repository PLAN or task dependencies.
- Do not widen scope or treat a derived design decision as a source requirement.
- Edit only the declared write set; request an orchestrator-approved change before crossing it.
- Escalate requirement conflicts, missing official inputs, and newly discovered work.

## Acceptance criteria

- [ ] The adapter is enabled only by explicit private configuration after provider/model approval; template mode remains valid without network/model dependencies.
- [ ] A legal Police action is selected and locked before a provider call; provider output cannot select, veto, delay, or mutate that action.
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

To be completed immediately before execution.

## Handoff contract

Report files changed, tests executed, exact test results, decisions made, deviations, blockers, and newly discovered work. Include command output or artifact paths sufficient for the orchestrator to validate every acceptance criterion.

## Result and evidence
