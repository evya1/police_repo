# PRD — Optional LLM text provider (police_repo)

## Outcome

Add an optional, provider-neutral text-rendering adapter. Deterministic code remains the sole authority for movement, barriers, truth/lie, landmark selection, validation, and fallback. Default/template mode performs no network call and records zero tokens.

## Functional requirements

- **LLM-01 Plan first:** after the action is immutable, local code creates `HintPlan(claim, target_landmark, fallback_text)`. `NON_CLAIM` has no landmark and is always rendered locally.
- **LLM-02 Minimal request:** the provider receives role, arena name, planned landmark, truth/lie label, style, and word cap only. Exact cells, grids, scent, belief, legal moves, opponent data, and movement reasoning are prohibited.
- **LLM-03 No authority:** the provider reply contains text plus usage/provider/model metadata. It cannot return verdict, action, barrier, target, score, or legality.
- **LLM-04 Strict validation:** normalize once to Unicode NFC, then accept only non-empty single-line text within `hint_max_words`, containing exactly the planned landmark, containing no other known landmark, coordinate-like text, control characters, JSON/code fencing, or unrequested metadata.
- **LLM-05 Deterministic fallback:** timeout, queue exhaustion, retry exhaustion, parse error, invalid text, or missing usage produces the plan's deterministic template. Action/verdict remain unchanged. Fallback reason is sealed for audit.
- **LLM-06 Typed port:** `TextProvider.render(HintRenderRequest, deadline=...) -> ProviderReply` is a one-method Protocol defined near `HintWriter`. Values are frozen data classes.
- **LLM-07 Central Gatekeeper:** all calls pass through `ExternalApiGatekeeper`; optional `llm` lane cannot consume the reserved `reporting` capacity.
- **LLM-08 Deadline:** no start or retry occurs when the estimated backoff/call budget exceeds the monotonic turn deadline.
- **LLM-09 Usage:** actual input/output tokens are recorded when supplied by the selected provider. Template/non-claim mode is exactly 0/0. Unknown provider usage remains `None`, not guessed; counted play fails closed because a fallback cannot erase tokens already consumed by the attempted call. Warmup may retain explicit unknown status.
- **LLM-10 Composition:** private config explicitly enables provider mode. Startup fails fast if enabled without a registered adapter/model. Tests inject a fake client; no test performs a live external call.
- **LLM-11 Vendor gate:** vendor SDK, environment-variable names, model identifier, prices, and rate settings are not chosen until PLANQ-003 is resolved.

## Non-goals

- LLM movement or barrier decisions, ranking, veto, legality repair, or fallback action.
- Sending private state or asking the model to infer a coordinate.
- Adding a vendor SDK before selection.
- Converting the synchronous application to asyncio.

## Acceptance gate

- Property test: for identical game seed/state, template, valid-provider, timeout, malformed-provider, and exception paths return identical action/barrier/verdict.
- Privacy test captures the exact provider request and asserts forbidden data/patterns are absent.
- Word cap uses configured `hint_max_words`, including values below 15.
- Concurrency tests prove queue bounds, lane reservation, deadline-aware retry, thread-safe counters, and no leaked active slots.
- Token totals reconcile provider reply -> decision evidence -> subgame -> series; template totals are zero.
- A post-move integration test proves the action/barrier are locked before the request and the planned landmark describes the destination rather than the pre-move cell.
- Full repository gates and cross-repo semantic parity pass with no network.
