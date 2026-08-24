---
id: T027
status: done
priority: P2
task_type: component
component: C02
optional: true
implements:
  - STRAT-008
  - SEC-009
context_files:
  - docs/components/C02-perception-strategy/PRD.md
  - docs/components/C02-perception-strategy/PLAN.md
  - docs/mechanisms/M-03-police-strategy.md
  - docs/PRD_llm_provider.md
  - docs/PLAN_llm_provider.md
read_set: []
depends_on:
  - T002
  - T007
  - T045
gates:
  - id: PLANQ-004
    kind: decision
    scope: provider_scope
    blocks: criterion
parallel_safe: true
claimed_by:
claim_expires_at:
write_set:
  - src/police_peer/strategy/hint_types.py
  - src/police_peer/strategy/hints.py
  - src/police_peer/strategy/inject.py
  - src/police_peer/strategy/decision.py
  - src/police_peer/wire/session.py
  - tests/unit/strategy/test_hint_types.py
  - tests/unit/strategy/test_hints.py
  - tests/unit/strategy/test_inject.py
  - tests/property/strategy/test_provider_invariance.py
risk: medium
---

# T027 — Deterministic hint plan and typed TextProvider port

## Expected outcome

Local deterministic code selects the action, the truth/lie claim, the target landmark, and the
verdict. A provider, if present, supplies wording only. Any provider failure falls back to the
deterministic template already associated with the selected plan, and the action, barrier, and
verdict are bit-for-bit unchanged.

## Requirements implemented

- `STRAT-008`
- `SEC-009` (sealed text/usage metadata only; aggregation belongs to T013)

## Relevant context

This task no longer chooses a vendor. Vendor selection is T050, gated by `PLANQ-003`.

T027 depends on **T045**, which owns `strategy/hints.py`, `strategy/inject.py`, and their unit
tests. The dependency is what serializes those shared paths; the two tasks must never run in the
same wave.

REVIEW_FINDINGS this task must close:

- **F-12** — the current seam sends the exact private position to the provider and accepts a
  provider-owned `verdict`.
- **F-13** — `HintWriter._cap(result.get("message", ""))` uses the default 15 rather than the
  configured `self.max_words`; exceptions are swallowed by a bare `except`; empty text can pass; and
  landmark/coordinate constraints are not validated.
- **F-14** — `resolve_brain(..., llm=...)` ignores `llm`, so the declared injection seam injects
  nothing.

## Gates

- `PLANQ-004` (`decision`, `blocks: criterion`) — the task may be claimed and implemented now; only
  the acceptance criterion scoped `provider_scope` waits.

## Constraints

- Edit only the declared write set.
- The public turn message and the `Decision` constructor stay source-compatible via defaults.
- Strategy imports no infrastructure and no vendor SDK.
- No DI framework, Repository/Unit of Work, event bus, runtime sibling import, live external call in
  tests, or guessed official/vendor contract.
- Every code and test file stays below 150 logical lines.

## Acceptance criteria

- [x] `hint_types.py` defines frozen `HintPlan`, `HintRenderRequest`, `TokenUsage`, `ProviderReply`,
      `HintResult`, and `FallbackReason`.
- [x] After the action is immutable, local code creates `HintPlan(claim, target_landmark,
      fallback_text)`; truth/lie/non-claim and landmark are local deterministic facts.
- [x] `claim=NON_CLAIM` has `target_landmark=None`, is rendered by a local deterministic line, and
      **never calls the provider**. No landmark is fabricated when the position belongs to no
      truth-compatible region.
- [x] `TextProvider.render(request, *, deadline)` receives only role, arena name, planned landmark,
      truth/lie label, style, and word cap. Exact cells, belief grid, scent field, opponent state,
      legal-move set, and movement reasoning are absent from the captured request.
      `{#provider_scope}`
- [x] The reply carries text plus usage/provider/model only; it can return no verdict, action,
      barrier, target, score, or legality.
- [x] Provider text is normalized once to Unicode **NFC** before validation and sealing.
- [x] Validation accepts only non-empty single-line text within the **configured** `self.max_words`
      (including values below 15), containing exactly the planned landmark, no other known landmark,
      no coordinate-like pattern, no control characters, and no JSON or code fencing.
- [x] Every typed and unexpected provider failure produces the plan's deterministic template and a
      recorded typed `FallbackReason`; no blanket silent `except`.
- [x] `resolve_brain` builds and passes a typed provider into `HintWriter`; the parameter is used or
      removed, never ignored.
- [x] Property tests prove action, barrier, verdict, **and target landmark** equality across
      template, provider success, timeout, malformed, and exception paths for an identical seed and
      state.
- [x] A post-move test proves the action and barrier are locked before the request is built and that
      the planned landmark describes the **destination** cell rather than the pre-move cell.
- [x] Text metadata is sealed for audit without being exposed on the public turn message.

## Verification

- `uv run pytest tests/unit/strategy/test_hint_types.py tests/unit/strategy/test_hints.py tests/unit/strategy/test_inject.py tests/property/strategy/test_provider_invariance.py`
- `uv run ruff check src tests`
- `uv run python scripts/check_line_cap.py`

## Result and evidence

Validated on `production-fixes`. The typed provider-neutral hint boundary, immutable-action
invariance, redacted request, deterministic fallback, Unicode validation, sealed usage metadata,
and composition wiring are covered by the task's unit and property tests. The combined completion
audit for T027/T033/T034/T046/T047/T048 passed 209 tests with no failures on 2026-08-24.
