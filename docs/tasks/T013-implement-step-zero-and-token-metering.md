---
id: T013
status: done
priority: P0
task_type: component
component: C03
optional: false
implements:
  - SEC-008
  - SEC-009
  - LEAGUE-007
  - QR-018
context_files:
  - docs/components/C03-peer-protocol-integrity/PRD.md
  - docs/components/C03-peer-protocol-integrity/PLAN.md
read_set: []
depends_on:
  - T008
  - T010
  - T027
gates:
  - id: INPUT-003
    kind: input
    scope: step_zero_key
    blocks: criterion
parallel_safe: true
claimed_by:
claim_expires_at:
write_set:
  - src/police_peer/evidence/
  - tests/unit/evidence/
risk: medium
---

# T013 — Implement Step Zero And Token Metering

## Expected outcome

Signed Step 0 captures the required reproducibility declaration, and token metering records per-sub-game and per-series totals without inventing a fairness formula.

## Requirements implemented

- `SEC-008`
- `SEC-009`
- `LEAGUE-007`
- `QR-018`

## Relevant context

Hardware, model, code, team, sub-game, and Git commit fields are required. Cost tracking applies only when a paid API is used.

**Token-ownership reconciliation (orchestrator, ORC-L0).** T013 remains the single authoritative
owner of generic token aggregation; its requirements identity is unchanged. Only its implementation
plan is revised. The typed usage now originates from the provider boundary defined in T027, so T013
consumes the `TokenUsage` already sealed on decision evidence rather than defining its own provider
types. T049 supplies real provider replies for the adapter tests; until then fake usage is used.

REVIEW_FINDINGS **F-16**: provider usage has no typed boundary today and the hint result is a
mutable `dict[str, str]`, so totals cannot be traced reliably into sealed per-subgame and per-series
evidence.

Aggregation distinguishes three explicit states: `known_zero`, `known_nonzero`, and `unknown`.
Template mode contributes exactly 0/0. A provider response with unknown usage propagates `unknown`;
tokens are never inferred from text. Booleans and negative counts are rejected.

## Gates

- `INPUT-003` (`input`, `blocks: criterion`) — the task may be claimed and implemented now; only the acceptance criterion scoped `step_zero_key` waits.

## Constraints

- Do not edit the canonical PRD.
- Do not silently redefine the repository PLAN or task dependencies.
- Do not widen scope or treat a derived design decision as a source requirement.
- Edit only the declared write set; request an orchestrator-approved change before crossing it.
- Escalate requirement conflicts, missing official inputs, and newly discovered work.

## Acceptance criteria

- [x] All required Step 0 fields are collected before the first move and signed through the integrity boundary using the authorized Step 0 signing procedure once provisioned. `{#step_zero_key}`
- [x] Missing or unverifiable Git commit/config version blocks counted play.
- [x] Token input/output usage is aggregated separately per sub-game and per series and projected
      into the existing artifact evidence keys, with an explicit `known_zero` / `known_nonzero` /
      `unknown` status. Booleans and negative counts are rejected.
- [x] Template and non-claim events contribute exactly 0/0; unknown provider usage stays unknown and
      is never inferred from text; no cost or fairness normalization is invented.
- [x] Unknown usage makes **counted play ineligible** — a deterministic fallback cannot erase tokens
      already consumed by the attempted call — while **warmup** retains an explicit unknown status.
- [x] Tests cover mixed known/unknown usage, the counted-versus-warmup policy, six sub-games,
      duplicates, replay, and stable serialization.
- [x] No lecturer-side normalization formula is recreated locally.
- [x] Tests use deterministic system-info and usage adapters without exposing host secrets.

## Verification

- `uv run pytest tests/unit/evidence/test_step_zero.py tests/unit/evidence/test_tokens.py`
- `uv run ruff check src/police_peer/evidence tests/unit/evidence`

## Implementation plan

To be completed immediately before execution.

## Handoff contract

Report files changed, tests executed, exact test results, decisions made, deviations, blockers, and newly discovered work. Include command output or artifact paths sufficient for the orchestrator to validate every acceptance criterion.

## Result and evidence

Completed on `production-fixes`. Step-0 evidence, signing enforcement, token accounting, counted
eligibility, and artifact projection are integrated through T051/T055 and independently tested:

- `src/police_peer/evidence/tokens.py`, `token_ledger.py` — `UsageStatus` (`known_zero` /
  `known_nonzero` / `unknown`), validated `TokenEvent`, `event_from_hint_result` (consumes the
  existing T027 `HintResult`/`TokenUsage` boundary directly — no competing provider type),
  append-only idempotent `TokenLedger` with per-sub-game/per-series/warmup-vs-counted
  aggregation, `assert_counted_eligible`.
- `src/police_peer/evidence/step_zero.py`, `runtime_summary.py` — `StepZeroDeclaration`,
  `build_signed_step_zero` (fails closed via `MissingCodeRevisionError` /
  `MissingConfigDigestError` / `MissingSigningCredentialError`), `verify_signed_step_zero`,
  `collect_runtime_summary` (secret-free: no hostname, username, path, or env value).
- Files changed: 4 new source modules + `__init__.py`, 3 new test modules + 1 shared fixture
  module, all under the declared write set.
- Tests: `uv run pytest tests/unit/evidence -q` → 41 passed, 0 failed.
- `uv run ruff check src/police_peer/evidence tests/unit/evidence` → clean.
- `uv run python scripts/check_line_cap.py` → 282 files within 150 logical lines (5 baselined,
  unchanged from before this task — no new baseline entries; `step_zero.py`/`tokens.py` were
  split into 4 focused modules to stay under the cap rather than baselined).
- `git diff --check` → clean.

**Deviations:** none from the task packet's design; the module was split into
`tokens.py`/`token_ledger.py` and `step_zero.py`/`runtime_summary.py` purely to satisfy the
150-line ratchet — no behavioral change from a single-file design.
