# PLAN — Optional LLM text provider (police_repo)

## Phase 0 — orchestrator decisions

The broad T027 outcome is split below. T027 owns the provider-neutral boundary, T050 owns the
resolved dependency-free OpenRouter transport, and T013 remains authoritative for generic token
aggregation. Template mode remains the default.

## T027 — deterministic hint plan and typed provider port

- Add `src/police_peer/strategy/hint_types.py` with frozen `HintPlan`, `HintRenderRequest`, `TokenUsage`, `ProviderReply`, `HintResult`, and `FallbackReason`.
- Rewrite `strategy/hints.py` into pure plan selection (truth/lie/non-claim), template rendering, NFC provider text validation, and a small `HintWriter` coordinator.
- Correct `strategy/inject.py` so the typed provider is actually injected.
- Extend `strategy/decision.py` and `wire/session.py` only with sealed text/usage/fallback metadata; public action contract remains source-compatible.
- Tests prove action/verdict invariance, privacy, validation, configured cap, and deterministic fallback.

## T048 — central Gatekeeper hardening

- Split typed config/errors/retry classification from coordination if needed to satisfy line cap.
- One thread-safe Gatekeeper, bounded global queue, global concurrency, per-lane concurrency/reservation, token buckets, daily quota, typed 429 retry, injected monotonic clock/sleeper, and deadline-aware backoff.
- Preserve existing reporting call behavior through a compatibility wrapper during migration; do not create a second gatekeeper.

## T049 — provider-neutral adapter

- Define a one-method `CompletionClient` Protocol owned by the adapter.
- Build a fixed-version prompt from `HintRenderRequest`; request plain text, not model-owned JSON semantics.
- Call only via `ExternalApiGatekeeper.execute(lane="llm", ...)`.
- Convert the injected client's response into `ProviderReply`; no vendor import and no environment read in the domain/strategy layer.

## T013 — token ledger integration

Update T013's implementation plan, not its requirements identity. Its evidence adapter consumes the typed usage already sealed in the decision, sums known integer input/output counts per subgame and series, and distinguishes `known_zero`, `known_nonzero`, and `unknown`. Unknown makes counted play ineligible but remains allowed and visible in warmup. Do not invent cost or fairness formulas.

## T050 — selected vendor transport (blocked: start by PLANQ-003)

Only after approval: add the selected SDK to `pyproject.toml` and lock, implement one `CompletionClient`, read its secret from the approved environment variable at the composition root, classify its typed rate/timeout errors, and add fake-transport contract tests. Live smoke evidence is manual/opt-in and sanitized.

## T051 — composition, cross-repo integration, evidence

- Add private `LanguageModelSettings` parsing in `wire/strategy_settings.py`/`wire/config.py`.
- Build provider/Gatekeeper in one composition root and pass the provider through `resolve_brain`.
- Integration tests cover disabled template mode, fake provider success, every fallback reason, token reconciliation, and lane isolation from reporting.
- Cross-repo parity tests compare provider request/result schemas and validation behavior.
- `scripts/smoke_llm_integration.py` runs template/fake scenarios through public composition; `scripts/benchmark_hint_path.py` records uninstrumented local overhead without a live provider.

## Dependency graph

T027 and T048 are parallel after orchestrator write-set approval. T049 depends on both. T013 token integration depends on T027 and may proceed with fake usage. T050 is separately gated. T051 depends on T013/T027/T048/T049 and depends on T050 only for the real-vendor configuration case.
