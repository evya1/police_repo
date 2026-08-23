# TODO — Optional LLM provider (police_repo)

## ORC-L0 — governance (`claude-opus-5`, main effort High)

- [x] Approve provider-as-wording-only ADR and privacy allowlist: ADR-010.
- [x] Amend T027; create T048–T051 with non-overlapping write sets and explicit sequencing dependencies for every shared path.
- [x] Keep PLANQ-003/T050 blocked until provider facts are written. `PLANQ-003 blocks: start` moved off T027 and onto T050; PLANQ-004 remains a T027 criterion gate.
- [x] Reconcile T013 ownership of token aggregation. T013 keeps its requirements identity and gains the revised implementation plan; the stale `T027 -> T013` edge is removed and `T013 -> T027` retained.

## T027 — hint boundary (`claude-sonnet-5`)

- [ ] Frozen types; provider reply has no verdict/action.
- [ ] Local plan selects truth/lie and landmark before provider call.
- [ ] Request allowlist excludes private state.
- [ ] Strict validator and configured word cap.
- [ ] Explicit non-claim plan; no provider call and no fabricated landmark.
- [ ] Normalize provider text to NFC before validation/sealing.
- [ ] Typed deterministic fallbacks; no blanket silent `except`.
- [ ] Action/barrier/verdict invariance property tests.

## T048 — Gatekeeper (`claude-sonnet-5`)

- [ ] Thread-safe state and real use of `concurrent_requests`.
- [ ] Bounded queue with deterministic deadline expiry.
- [ ] `reporting` and `llm` lane policies under one object.
- [ ] Injected monotonic clock/sleeper; typed retry predicate.
- [ ] No permit/counter leak under success or exception.

## T049 — neutral adapter (`claude-sonnet-5`)

- [ ] Narrow `CompletionClient`; no vendor SDK.
- [ ] Versioned prompt from allowlisted fields only.
- [ ] Gatekeeper `llm` lane call and typed reply/usage conversion.
- [ ] Fake-client tests; no live network.

## T013 — usage evidence (`claude-sonnet-5`)

- [ ] Aggregate input/output separately per subgame/series.
- [ ] Preserve unknown; template equals exactly zero.
- [ ] Unknown usage blocks counted play but remains explicit in warmup.
- [ ] Reconcile evidence with sealed decision metadata.

## T050 — vendor adapter (blocked until PLANQ-003)

- [ ] Approved SDK/model/env/rates/budget recorded.
- [ ] Dependency and lock updated with no unrelated drift.
- [ ] Typed error mapping and fake-transport tests.

## T051 — integration (`claude-haiku-4-5-20251001` scaffolding; `claude-sonnet-5` implementation/review)

- [ ] Private config and fail-fast composition.
- [ ] Template/fake-provider/failure integration matrix.
- [ ] Reporting lane remains usable under saturated LLM lane.
- [ ] Run fake-only LLM smoke and uninstrumented hint-path benchmark scripts.
- [ ] Both repo gates and schema/parity tests pass.
