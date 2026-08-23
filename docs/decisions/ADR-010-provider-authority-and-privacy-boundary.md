---
artifact: adr
id: ADR-010
status: accepted
date: 2026-08-23
owners: orchestrator
related_requirements: [STRAT-008, SEC-009, QR-008, QR-018]
related_tasks: [T013, T027, T048, T049, T051]
supersedes:
---

# ADR-010 — The language-model provider has no authority and receives no private state

## Context

The verbal hint channel is the one place where this peer may talk to an external model. At the
reviewed baseline that seam did two things it must never do. `TextProvider.generate` received the
peer's exact private position, and it returned a `verdict` that the caller adopted. A provider could
therefore both learn the hidden state the whole game is built on and decide whether this peer had
told the truth about it.

The surrounding code compounded the problem. The configured word cap was ignored in favour of a
hard-coded 15; a bare `except Exception: pass` swallowed every provider failure without recording
one; empty text passed validation; and the declared injection seam, `resolve_brain(..., llm=...)`,
ignored its own argument, so nothing was ever injected.

Two related honesty problems sit next to it. Some positions belong to no truth-compatible landmark
region, so a `target_landmark: str` forces the code to invent a claim it cannot support. And token
usage had no typed boundary, so totals could not be traced from a provider reply into sealed
evidence.

## Decision

**Movement is decided first and is never revisited.** The action and barriers are locked before any
text work begins. Provider failure cannot change, delay beyond the deadline, veto, or reorder an
action.

**Truth, lie, and non-claim are local facts.** Local deterministic code selects the claim, the target
landmark, and the verdict, and computes the deterministic fallback text at the same time. A
`NON_CLAIM` plan carries `target_landmark=None`, is rendered by a local line, and **never calls the
provider**: no landmark is fabricated for a position that has none.

**The provider receives an allowlist and returns wording only.** `HintRenderRequest` carries role,
arena name, planned landmark, truth/lie label, style, and word cap — nothing else. Exact cells, the
belief grid, the smell field, opponent state, the legal-move set, and movement reasoning are
prohibited. `ProviderReply` carries text, usage, provider, and model. It cannot carry a verdict,
action, barrier, target, score, or legality, and the code never reads one.

**Validation is strict and failure is typed.** Text is normalized once to Unicode NFC, then accepted
only if it is non-empty, single-line, within the **configured** `max_words`, contains exactly the
planned landmark, contains no other known landmark, and contains no coordinate syntax, control
character, or code fence. Any typed or unexpected failure produces the already-planned deterministic
template plus a recorded `FallbackReason`. No blanket silent `except` remains.

**Every external call passes the one Gatekeeper.** `reporting` and `llm` are distinct lanes inside a
single `ExternalApiGatekeeper`. Optional LLM traffic can never consume the capacity reserved for
mandatory reporting, and no retry or backoff may start when the remaining monotonic deadline budget
cannot cover it.

**Usage is typed, and unknown stays unknown.** Template and non-claim modes report exactly 0/0. A
provider that supplies counts has those counts recorded; a provider that does not leaves `None`.
Tokens are never inferred from text. Unknown usage makes **counted play ineligible** — a fallback
does not erase the tokens an attempted call already consumed — while warmup may retain an explicit
unknown status.

**No vendor is chosen here.** PLANQ-003 is only partially resolved: template mode is sufficient for
the core MVP, and the provider, model, cadence, budget, and rate limits remain a team decision. No
SDK, environment variable name, price, or rate constant is introduced until T050's gate resolves.

## Alternatives considered

- **Let the provider return the verdict.** Rejected: it hands audit semantics to an external service
  and makes the peer's own truthfulness record unverifiable.
- **Send the position and ask for a hint.** Rejected: it leaks the hidden state the game protects,
  and no amount of prompt instruction makes that safe.
- **Fabricate a landmark when none is truth-compatible.** Rejected: it manufactures a claim the peer
  cannot stand behind. `NON_CLAIM` states the honest thing instead.
- **Estimate tokens from text length when the provider omits usage.** Rejected: an invented number
  that looks like evidence is worse than an explicit unknown.
- **Give the LLM its own gatekeeper.** Rejected: two gatekeepers cannot enforce one global budget,
  and optional traffic would compete with mandatory reporting.
- **Convert the application to asyncio to call a provider.** Rejected: a large, risky change to the
  whole runtime in exchange for one optional, bounded, synchronous call.

## Consequences

Positive: the game's hidden state never leaves the process; audit semantics stay local and
deterministic; identical seeds produce identical actions and verdicts whether the provider succeeds,
times out, or is absent; and token evidence is traceable end to end.

Negative: prose quality is bounded by what a landmark-only request can produce, and the strict
validator rejects otherwise-pleasant text that mentions a second landmark. Both are accepted: the
deterministic template is a fully legal way to play a complete game.

Verification: because the provider cannot influence anything but wording, provider behaviour is
tested entirely with fakes. No test performs a live external call.

## Validation

- Property tests: identical action, barrier, verdict, and target landmark across template, success,
  timeout, malformed, and exception paths for one seed and state.
- Privacy test captures the exact request after a post-move decision and asserts no cell, grid,
  scent, belief, legal-move set, or reasoning appears in it.
- Post-move test proves the planned landmark describes the destination, not the pre-move cell.
- Non-claim test proves no provider call occurs and no landmark is invented.
- Cap test uses a configured value below 15 and proves 15 is never hard-coded.
- Gatekeeper tests use fake time and barriers to prove lane reservation under LLM saturation,
  bounded queueing, deadline-aware retry, and no leaked permits.
- Token reconciliation runs provider reply -> sealed decision -> subgame -> series; template totals
  are exactly zero and unknown totals block counted play.

## Approval

- Decision owner: orchestrator
- Approved by: orchestrator (ORC-L0)
- Approval date: 2026-08-23
