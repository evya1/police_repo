---
id: T048
status: done
priority: P0
task_type: component
component: C06
optional: false
implements:
  - QR-008
context_files:
  - docs/components/C06-reporting-league/PRD.md
  - docs/components/C06-reporting-league/PLAN.md
  - docs/PRD_llm_provider.md
  - docs/PLAN_llm_provider.md
read_set: []
depends_on:
  - T002
  - T017
  - T017
gates: []
parallel_safe: true
claimed_by:
claim_expires_at:
write_set:
  - src/police_peer/infra/external_api_gatekeeper.py
  - src/police_peer/infra/gatekeeper_types.py
  - src/police_peer/infra/retry_policy.py
  - tests/unit/infra/test_external_api_gatekeeper.py
  - tests/unit/infra/test_gatekeeper_concurrency.py
  - tests/unit/infra/test_retry_policy.py
risk: high
---

# T048 — Thread-safe deadline-aware central Gatekeeper

## Expected outcome

One `ExternalApiGatekeeper` owns global and per-service limits. Optional LLM traffic can never
consume the capacity reserved for mandatory reporting, and no retry or backoff can overrun the
turn deadline.

## Requirements implemented

- `QR-008`

## Relevant context

REVIEW_FINDINGS **F-15**: `concurrent_requests` is unused; `_active_calls` is compared against
`queue_depth` rather than a concurrency limit; state is not thread-safe; excess work is rejected
rather than queued; and retry sleeps are global `time.sleep` calls that can overrun the turn
deadline.

There is exactly one Gatekeeper. This task hardens it; it does not create a second one.

T048 depends on **T017**, which owns `infra/external_api_gatekeeper.py` and its unit test. The
dependency is what serializes that shared path; the two tasks must never run in the same wave.

T048 depends on **T017**, which owns `infra/external_api_gatekeeper.py` and its unit test. The
dependency is what serializes that shared path; the two tasks must never run in the same wave.

## Constraints

- Edit only the declared write set.
- Preserve an adapter-compatible `execute(call, ...)` path for current reporting callers while
  introducing explicit lane and deadline arguments.
- Inject the monotonic clock and the sleeper/wait abstraction; tests use fake time, never real sleep.
- Release every counter and permit in `finally`.
- The application stays synchronous; it is not converted to asyncio to call a model provider.
- Every code and test file stays below 150 logical lines; extract typed config, errors, and retry
  classification so the coordinator stays under the cap.

## Acceptance criteria

- [x] One `Lock`/`Condition`-protected state machine enforces the global active count, the configured
      `concurrent_requests`, a bounded waiting count, the token bucket, the daily quota, and per-lane
      limits and reservations.
- [x] Excess work queues until a permit or the deadline; `QueueFull` is raised only at real capacity.
- [x] `reporting` and `llm` are distinct lanes inside the single Gatekeeper, and a saturated `llm`
      lane leaves the `reporting` reservation usable.
- [x] Retries occur only for typed or transparently classified 429/transient errors, and the
      remaining deadline budget is proven before any sleep or retry.
- [x] Tests use barriers and fake time to prove maximum concurrency, FIFO or a documented
      deterministic queue discipline, reporting reservation under LLM saturation, deadline expiry,
      daily reset, the retry schedule, and no leaked permits or counters on success or exception.
- [x] No live external call occurs in any test.

## Verification

- `uv run pytest tests/unit/infra/test_external_api_gatekeeper.py tests/unit/infra/test_gatekeeper_concurrency.py tests/unit/infra/test_retry_policy.py`
- `uv run ruff check src/police_peer/infra tests/unit/infra`
- `uv run python scripts/check_line_cap.py`

## Result and evidence

Validated on `production-fixes`. The single condition-protected Gatekeeper enforces bounded
concurrency, lane reservation, deterministic queuing, deadlines, quota/token limits, and typed
retry policy without live network calls in tests. The combined completion audit passed 209 tests
with no failures on 2026-08-24.
