---
artifact: adr
id: ADR-004
status: accepted
date: 2026-08-16
owners: orchestrator
related_requirements: [STRAT-002, STRAT-003, STRAT-004, STRAT-005, NET-001, NET-002, NET-003, NET-004, CFG-006]
related_tasks: [T005, T008, T009, T022]
supersedes:
---

# ADR-004 — Kit-First Interoperability Profile

Use an ADR only for a sufficiently important and durable technical design decision. Official-input receipt belongs in the Input Register, product/requirement changes belong in a Change Request, and execution work belongs in a task. This decision selects a runtime interoperability profile; it adds, removes, and normatively changes no canonical requirement, so no Change Request applies. Tracked by GitHub Issue #6.

## Context

Two independently written peers must compute byte-identical scent arithmetic and speak an identical wire shape, or they diverge silently with no error either side can detect alone. Our canonical requirements fix the parameters (`CFG-006`: centre `0.9`, decay `0.10`, 5×5 field) and the recurrence (`STRAT-003`), but the book leaves the repeated-emission/saturation, merge, and update-order behaviour unstated — that is `OPEN-009`, and no official Moodle artifact or written lecturer clarification has answered it.

Until now our planning artifacts responded to that gap by forbidding the selection of any production default before an official answer arrived. That was the correct posture while nothing else supplied enough information to build against. It is no longer the correct posture, because it now blocks work indefinitely on an answer we do not control, and because a concrete, reproducible compatibility target exists.

The project team wants the first working implementation to interoperate directly with the current `Imreec/copthief-league-protocol` kit, especially its runnable `sparring` peer. That kit was inspected read-only at upstream commit `ad6557626587e09146af4283a5e808e7001343c5` and treated as `EVID-003`, **NON-AUTHORITATIVE interoperability evidence**, never a course input. What it supplies is two fully specified, separately registered scent models with pinned parameter documents and published conformance vectors, plus a documented wire profile whose tool surface has carried real cross-team series.

The decisive observation is that the kit registers *two* scent models rather than one. It does not resolve the book's ambiguity; it works around it exactly as we must — by naming each candidate, pinning it, and making peers declare which one they compute so a mismatch is caught before play instead of during it.

## Decision

Adopt one default interoperability profile and one additional supported scent profile.

**Default profile:**

| Axis | Value |
|---|---|
| `wire_shape` | `reference-v3` |
| `scent_model` | `subtractive_chebyshev_v1` |
| `info_mode` | `belief` |
| `smell_binding` | current/unbound behaviour; the proposed `commit_grid_v1` extension is **not** adopted |
| turn order | the `reference-v3` convention — the thief takes the first game turn |

The required `smell_grid` turn-message key is preserved, because `reference-v3` transmits the field rather than recomputing it.

The turn-order convention is load-bearing and is recorded explicitly because the `wire_shape` declaration does not cover it: two peers whose locks all match can still each wait for the other forever after a fully successful handshake. In this repository's natural Police role, that means our peer waits for the opponent's opening turn rather than opening the game itself.

**Additionally supported scent profile:** `multiplicative_book_v1`, the explicit book-oriented alternative. It is implemented, vector-tested, and selectable. It is not deleted, downgraded, or folded into the default merely because it is not the default.

The full arithmetic of both profiles is recorded once, in `docs/mechanisms/M-01-scent-model.md` §B; the full wire surface is recorded once, in `docs/contracts/CT-03-peer-wire.md`. This ADR does not restate either.

## Why

Immediate interoperability with the current `copthief-league-protocol` sparring peer is our first integration target. It is the only opponent available to us today that is runnable on demand, independently written, and byte-pinned — which makes it the cheapest way to discover a divergence while nothing is at stake. `subtractive_chebyshev_v1` is what `wire_shape: reference-v3` actually carries, so choosing it as the default is what makes a sparring run work without a negotiation round-trip about physics.

`smell_binding: commit_grid_v1` is deliberately excluded: it is `PROPOSED` upstream, no implementation has shipped it, and it changes a commit preimage. It must not sit on our critical path.

## Authority boundary

This is an **engineering decision about what we build**, not a reading of the source.

- It does **not** close `OPEN-009`. `official_status` for `OPEN-009` remains `OPEN`.
- It is **not** a lecturer clarification, not a Moodle artifact, and not an official resolution of section 4.3. No project artifact may state that the kit resolved `OPEN-009`, that a lecturer clarified it, or that the official model is subtractive.
- It does **not** override the project book or the official software-quality guide. The source authority order is unchanged: official sources first, our canonical requirements second, the kit third as conformance evidence, our profile decisions fourth.
- Neither profile in `M-01` §B may be described as the officially correct reading. `multiplicative_book_v1` is the closest reading of the printed figure, but its upper clamp, evaluation order, and no-rounding policy are still interpretation.
- A future official clarification can require an adapter or profile change. That is expected and cheap by construction, which is the point of keeping the selection behind an interface.

What `OPEN-009` no longer does is block implementation. Scent implementation, default-model selection, model-lock generation and declaration, local testing, and uncounted sparring all proceed against this profile. Confirmation against an official answer happens before counted play.

The same principle applies generally: where a non-authoritative interoperability profile supplies enough information to implement, an unresolved official ambiguity narrows to the claim of official correctness rather than blocking the build.

## Alternatives considered

- **The book profile (`multiplicative_book_v1`) as the only or default implementation.** Rejected as the *default*, not as a profile — it stays fully supported. As a default it maximises apparent fidelity to the printed figure while minimising interoperability: it is not what `reference-v3` carries, it is not transmitted (each side recomputes the rival's field), and a sparring run against the current peer would have to renegotiate physics before it could start. It also would not actually settle `OPEN-009`, since its upper clamp and evaluation order are themselves interpretation.
- **The kit reference profile only, dropping the book model.** Rejected: it deletes the reading closest to the printed source on the strength of a non-authoritative target, which inverts the authority order this project is built on. If an official clarification later favours the book's arithmetic, we would have discarded the implementation we need, and the compatibility argument for the reference profile would not survive that clarification.
- **Continue selecting nothing until `OPEN-009` is officially answered.** Rejected: it blocks `T005`, and through it belief and strategy, on an external answer with no committed date, while a sufficient basis to build already exists. It also leaves the model-lock behaviour (`STRAT-005`) untested until very late, which is precisely the kind of interoperability defect that is cheapest to find early.
- **Support both models, with the kit reference profile as the default — SELECTED.** Keeps the book reading implemented and testable, makes sparring against the current peer work out of the box, and turns the unresolved ambiguity into a declared, checkable runtime choice instead of a silent assumption.

## Consequences

- Two scent implementations exist behind one small common interface. Belief and strategy consume the selected profile through that boundary and never branch on which model is active.
- Model selection is an explicit runtime/profile configuration value, read through the existing local private-configuration seam owned by `T003`. It is not an Appendix F term, is not a secret, and never weakens a signed shared value. No change to `T003` is required.
- The selected model is declared as a hash over a pinned parameter document, alongside the wire, info-mode, and smell-binding declarations, and outside the closed signed-terms set. A mismatch refuses the start with a diagnostic and no partial game state; a peer that declares nothing is not a mismatch.
- Vector/golden tests cover **both** registered models, plus repeated-emission/saturation, edges, corners, and clipping.
- Default sparring compatibility: a run against the current kit peer needs no physics renegotiation.
- `T005`'s scope grows slightly — a second model and a selection seam — but stays one bounded task. It is not split, and it is not renumbered.
- `T009` gains a concrete, locally provable wire target instead of an invented envelope. `T008` gains published golden vectors to prove its own byte-level primitives against early rather than deferring every check to `T022`.
- This ADR is limited to protocol-level interoperability. Gameplay policy, heuristics, search behaviour, and strategy design remain independent; compatibility is implemented through local adapters, profile definitions, and conformance tests.
- Negative: two arithmetic implementations to maintain, and a declared profile that must stay consistent between our configuration, our lock document, and our documentation. Mitigated by both models being pinned to published vectors, so drift fails a test rather than a match.

## Revisit conditions

Revisit this decision if any of the following occurs:

- The lecturer supplies an official clarification of the section 4.3 saturation/merge/update-order question.
- An official Moodle artifact pins bytes or semantics incompatible with the adopted profile.
- A counted opponent requires a mutually agreed alternative profile.

In each case the profile or adapter changes; the canonical requirements do not.

## Validation

- `scripts/check_planning_graph.py` passes: 29 tasks, 6 components, dependency graph unchanged and acyclic.
- `scripts/run_quality_gates.py` passes, including link and secret checks.
- Every shared artifact touched by this decision remains byte-identical in both role repositories.
- `docs/spec/OPEN_QUESTIONS.md` still records `OPEN-009` with `official_status: OPEN`.
- No application source, no `uv.lock`, and no runtime dependency change accompanies this decision.

## Approval

- Decision owner: orchestrator
- Approved by: project team (human-approved engineering/interoperability decision)
- Approval date: 2026-08-16
