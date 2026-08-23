---
id: T051
status: not_started
priority: P2
task_type: integration
component: C06
optional: true
implements:
  - STRAT-008
  - SEC-009
  - QR-006
  - QR-018
context_files:
  - docs/components/C06-reporting-league/PRD.md
  - docs/components/C06-reporting-league/PLAN.md
  - docs/PRD_llm_provider.md
  - docs/PLAN_llm_provider.md
read_set: []
depends_on:
  - T013
  - T027
  - T046
  - T047
  - T048
  - T049
gates:
  - id: PLANQ-003
    kind: decision
    scope: real_vendor_configuration
    blocks: criterion
parallel_safe: false
claimed_by:
claim_expires_at:
write_set:
  - src/police_peer/wire/strategy_settings.py
  - src/police_peer/wire/config.py
  - src/police_peer/runner.py
  - src/police_peer/sdk.py
  - tests/unit/wire/test_llm_config.py
  - tests/integration/test_llm_hint_pipeline.py
  - tests/integration/test_gatekeeper_lane_isolation.py
  - tests/contract/test_cross_repo_llm_contract.py
  - tests/fixtures/llm/provider_contract_v1.json
  - scripts/smoke_llm_integration.py
  - scripts/benchmark_hint_path.py
risk: high
---

# T051 — LLM composition, configuration, integration, and parity

## Expected outcome

One composition root parses private configuration, constructs the single Gatekeeper with a reserved
reporting lane, builds the provider, and passes it through `resolve_brain`. Disabled mode builds no
client and performs no network call. Both repositories validate a provider reply identically.

## Requirements implemented

- `STRAT-008`
- `SEC-009`
- `QR-006`
- `QR-018`

## Relevant context

Implements LLM-10 of `docs/PRD_llm_provider.md`.

This task depends on **T046 and T047 in addition to the LLM chain**: its write set shares
`src/police_peer/runner.py` with T046 and `src/police_peer/sdk.py` with T047. The dependency is what
serializes those shared paths; the three tasks must never run in the same wave.

`parallel_safe` is `false` for the same reason.

## Gates

- `PLANQ-003` (`decision`, `blocks: criterion`) — the disabled/template and fake-provider matrix is
  implemented and verified now; only the real-vendor configuration criterion waits.
  `{#real_vendor_configuration}`

## Constraints

- Edit only the declared write set.
- One composition function receives an already-created `CompletionClient` factory. No container, no
  service locator, no DI framework.
- CLI and SDK signatures stay compatible through defaults.
- No live external call in any test.
- Every code and test file stays below 150 logical lines.

## Acceptance criteria

- [ ] Private configuration is parsed once into frozen `LanguageModelSettings` defaulting to
      disabled/template mode.
- [ ] Enabled mode without a registered adapter and model fails fast at startup; disabled mode builds
      no client at all.
- [ ] Exactly one Gatekeeper is constructed and the reporting lane capacity is reserved.
- [ ] The integration matrix covers disabled template mode, non-claim, fake provider success, every
      fallback class, post-move destination semantics, deadline expiry, counted-versus-warmup token
      reconciliation, and a saturated LLM lane while reporting still succeeds.
- [ ] `scripts/smoke_llm_integration.py` runs the scripted-fake scenarios through the public
      composition path and never accepts credentials or contacts a live service.
- [ ] `scripts/benchmark_hint_path.py` measures template and fake-provider/Gatekeeper overhead in a
      fresh **uninstrumented** subprocess with `perf_counter_ns`, reporting environment, sample
      count, p50, p95, and p99. It is informational, not a correctness gate, and never measures a
      real provider round trip.
- [ ] The cross-repo contract test uses the same request fixture in both repositories and expects
      semantically identical reply validation, with only package and role names differing.
- [ ] Template and non-claim modes report exactly zero tokens; unknown provider usage stays unknown
      and makes counted play ineligible while remaining explicit in warmup.
- [ ] Real-vendor configuration is verified only after `PLANQ-003` resolves.
      `{#real_vendor_configuration}`

## Verification

- `uv run pytest tests/unit/wire/test_llm_config.py tests/integration/test_llm_hint_pipeline.py tests/integration/test_gatekeeper_lane_isolation.py tests/contract/test_cross_repo_llm_contract.py`
- `uv run python scripts/smoke_llm_integration.py --scenario template --json`
- `uv run python scripts/benchmark_hint_path.py --help`
- `uv run ruff check .`
- `uv run pytest`
- `uv run python scripts/run_quality_gates.py`

## Result and evidence

(to be filled)
