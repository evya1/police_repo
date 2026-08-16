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

# ADR-004 — Operational Interoperability Profile

Use an ADR only for a sufficiently important and durable technical design decision. Official-input receipt belongs in the Input Register, product/requirement changes belong in a Change Request, and execution work belongs in a task. This decision records a set of operational conventions; it adds, removes, and normatively changes no canonical requirement, so no Change Request applies.

## Context

Two independently written peers must compute byte-identical scent arithmetic and speak an identical wire shape, or they diverge silently with no error either side can detect alone.

The canonical requirements fix the scent parameters (`CFG-006`: centre `0.9`, decay `0.10`, 5×5 field) and the recurrence (`STRAT-003`). They do not fix the repeated-emission/saturation behaviour, the merge rule, or the deposit-versus-decay order — that gap is `OPEN-009`, and no official artifact or written lecturer clarification has closed it. The official requirements likewise fix that peers communicate over FastMCP (`NET-001`…`NET-004`) without fixing the tool names, argument names, turn-message keys, or which side takes the first game turn.

Implementation cannot wait for those details. Every one of them must be a single deterministic choice before two peers can exchange a first message, and each choice is invisible in a successful handshake if the two sides differ. This ADR therefore records the project's operational conventions for the interoperability boundary: binding for this implementation, verified by deterministic vectors, and replaceable through an adapter if a later authoritative clarification requires other behaviour.

## Decision

### Selected profile

| Axis | Selected value |
|---|---|
| `wire_shape` | `reference-v3` |
| `scent_model` | `subtractive_chebyshev_v1` (default) |
| `scent_model` | `multiplicative_book_v1` (additionally supported and selectable) |
| `info_mode` | `belief` |
| `smell_binding` | current/unbound; the `commit_grid_v1` extension is **not** adopted |
| turn order | the thief takes the first game turn |

`reference-v3`, `subtractive_chebyshev_v1`, `multiplicative_book_v1`, `belief`, and `commit_grid_v1` are machine-readable protocol literals. They are compared as exact strings across peers and must never be renamed, re-cased, or translated in configuration, declarations, or code.

### Scent

Two scent profiles are implemented behind one common interface, and exactly one is active per pairing. `subtractive_chebyshev_v1` is the default because `wire_shape: reference-v3` transmits the field it produces, so a run needs no negotiation round-trip about scent arithmetic. `multiplicative_book_v1` follows the multiplicative decay form the source states and stays fully implemented, vector-tested, and selectable; it is not folded into the default.

The two profiles differ in decay form, update order, rounding, upper clamp, and transport. They are two models, not two spellings of one model. The complete arithmetic of each is recorded once in `docs/mechanisms/M-01-scent-model.md` §B and is not restated here.

### Turn order

Turn order is recorded explicitly because the `wire_shape` declaration does not carry it. Two peers whose declarations all match can still each wait for the other forever after a fully successful handshake. In this repository's Police role, the peer waits for the opponent's opening turn rather than opening the game itself.

### Model declaration

The active value for each of `scent_model`, `wire_shape`, `info_mode`, and `smell_binding` is declared at negotiate time as a SHA-256 hash over a pinned parameter document, under the key `<family>_sha256`. The document itself never crosses the wire. Hashing a pinned field set — rather than a bare model name or an ad-hoc dictionary — is what makes two independent implementations' declarations comparable at all.

Declarations sit outside the closed signed-terms set, because the signed terms are a flat closed key list and adding a profile key to them would invalidate the signature.

**Refusal rule:** refuse the start only when both peers declare a family and their declared hashes disagree. Omission is never refusal — one side declaring while the other is silent still plays. A refused start produces a diagnostic and no partial game state.

### Wire surface

The tool surface, argument names, required turn-message keys, and validation order are recorded once in `docs/contracts/CT-03-peer-wire.md` and are not restated here. The whole surface is exercisable as two local processes with no public endpoint, tunnel, or opponent URL.

### Authority boundary

These are operational conventions, not requirements.

- They do not close `OPEN-009`, `OPEN-007`, or `OPEN-001`. Each `official_status` is unchanged.
- Neither scent profile may be described anywhere as the officially correct reading of the source. `multiplicative_book_v1` follows the printed decay form, but its upper clamp, evaluation order, and no-rounding policy remain interpretation.
- The source authority order is unchanged: official specification and official software-quality guide first, canonical requirements second, these operational conventions last.
- Confirmation that the selected profile is acceptable for counted play happens before the `pairing_preflight` gate.

What these conventions do is unblock implementation. Scent implementation, default selection, model-lock generation and declaration, local testing, and uncounted external play all proceed against them.

## Alternatives considered

- **`multiplicative_book_v1` as the only or default model.** Rejected as the default, not as a profile — it stays fully supported. It is not the arithmetic `reference-v3` transmits, it is recomputed rather than transmitted, and selecting it as the default would require renegotiating scent arithmetic before any run can start. It would also not settle `OPEN-009`, since its upper clamp and evaluation order are themselves interpretation.
- **`subtractive_chebyshev_v1` only, dropping the book-form model.** Rejected: it discards the reading closest to the printed source. If a later clarification favours the multiplicative form, the needed implementation would already have been deleted.
- **Select nothing until `OPEN-009` is officially answered.** Rejected: it blocks `T005`, and through it belief and strategy, on an external answer with no committed date, and it leaves the model-lock behaviour (`STRAT-005`) untested until very late — the class of interoperability defect that is cheapest to find early.
- **Adopt `smell_binding: commit_grid_v1`.** Rejected: it changes a commit preimage and no implementation depends on it. It must not sit on the critical path.
- **Support both models with `subtractive_chebyshev_v1` as the default — SELECTED.** Keeps both readings implemented and testable, needs no negotiation round-trip to start a run, and turns an unresolved ambiguity into a declared, checkable runtime value instead of a silent assumption.

## Consequences

- **Deterministic cross-peer behaviour.** Every value above is either transmitted or declared as a hash, so a mismatch is detected at negotiate time rather than discovered as divergent belief mid-game.
- **Golden-vector verification.** Both scent profiles, the canonical-byte primitives, and the declaration hashes are proven against deterministic vectors committed in the repository. Drift fails a test rather than a match. `T005` owns the scent vectors, `T008` the canonical-byte vectors, `T009` the wire surface and turn order; `T022` re-runs them end to end rather than exercising them for the first time.
- **Adapter boundary.** Every convention above lives behind the transport/profile adapter boundary. Belief, strategy, and the domain core consume the selected profile through one interface and never branch on which model is active, so a later authoritative requirement changes a profile or an adapter, never the domain.
- **Failure before counted play.** When a peer declares a family whose value disagrees with ours, the start is refused with a diagnostic naming the disagreeing family and no partial game state is created. Negotiated terms that cannot be satisfied fail before counted play rather than during it.
- **Maintenance cost.** Two scent arithmetics must be maintained, and the declared profile must stay consistent across configuration, the lock document, and this ADR. Both models are pinned to committed vectors, which converts that risk into a failing test.
- **Scope.** This ADR is limited to the interoperability boundary. Gameplay policy, heuristics, and search behaviour are independent of it.

## Revisit conditions

- An official clarification of the section 4.3 saturation/merge/update-order question is registered and verified.
- An official artifact pins bytes or semantics incompatible with a convention above.
- A counted opponent requires a mutually agreed alternative profile.

In each case the profile or adapter changes; the canonical requirements do not.

## Validation

- `scripts/check_planning_graph.py` passes: 29 tasks, 6 components, dependency graph unchanged and acyclic.
- `scripts/run_quality_gates.py` passes, including link, secret, and documentation-language checks.
- Every shared artifact touched by this decision is byte-identical in both role repositories.
- `docs/spec/OPEN_QUESTIONS.md` records `OPEN-009` with `official_status: OPEN`.

## Approval

- Decision owner: orchestrator
- Approved by: project team
- Approval date: 2026-08-16
