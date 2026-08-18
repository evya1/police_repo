---
artifact: component-prd
id: PRD-C02
component: C02
status: draft
shared: core; role sections in M-03/M-04
owner: orchestrator
updated: 2026-08-16
---

# C02 — Perception & Strategy

## Purpose

Own everything a role needs to decide its next legal action under partial observability: the deterministic scent model both peers must compute identically, the local probabilistic belief this role forms about the opponent, and the boundary that isolates verbal-hint generation from movement selection. The role-specific decision policy itself (pursuit vs. evasion) is intentionally out of scope here — it lives in the role-specific mechanism PRDs M-03 (Police) and M-04 (Thief), so this document stays shared.

## Requirements owned (primary)

ARCH-007 (strategy is a separate module from communication/orchestration/logging); STRAT-001…009 (scent emission/decay, belief maintenance, movement-policy freedom, verbal-hint boundary, hint negotiability). 10 requirements total.

## Requirements consumed / affected

- GAME-004…011 (C01): strategy selects only from the legal-action set C01 exposes; it never invents a legal action.
- CFG-006 (C01): the Fixed scent parameters (center 0.9, decay 0.10, 5×5 field) are consumed here, not redefined. The scent-profile *selection* is a local, non-shared configuration value read through C01's existing private-configuration seam; it is not an Appendix F term and never weakens a signed shared value.
- OBS-003 (C05): the belief heatmap projects this component's belief output verbatim.
- SEC-009, QR-018 (C03/C06): token metering for an optional language-model provider is reported by C06/C03, not computed here.

## Observable behavior

- On every move or stay, the role emits a 5×5 scent field around its position with fixed center intensity 0.9 and the agreed radial profile (STRAT-002).
- After a full turn by both sides, each scent cell decays and absorbs new emission. The **selected scent profile supplies the complete emission-and-decay arithmetic** used at runtime — not merely the saturation/merge/update-order details the source leaves open (OPEN-009). See M-01 §B.
  - `multiplicative_book_v1` follows the book-style multiplicative recurrence `tau_ij(t+1) = max(0, (1-0.10)*tau_ij(t) + delta_tau_ij)` (STRAT-003).
  - `subtractive_chebyshev_v1` uses the subtractive arithmetic `round(max(0, tau - 0.1), 3)` and therefore **intentionally diverges from the source's multiplicative decay form**.
  - The project supports both behind one interface, defaulting to `subtractive_chebyshev_v1` because that is the arithmetic `wire_shape: reference-v3` transmits. That default is an operational convention (ADR-004): it does not modify the official or canonical requirement and does not close OPEN-009.
- The active profile is chosen once, by configuration, at the component boundary; no conditional on model identity is spread through belief or strategy code.
- The role reads only the opponent's scent field and its own hints, never plants scent it does not occupy (STRAT-004).
- The belief map updates from scent and hints and materially influences legal move selection for both roles (STRAT-006) — see M-02 for the invariants this update must hold.
- Verbal text uses the recommended zero-token template mode by default, or an optionally configured provider limited to text/behavioral analysis unless movement use is explicitly, mutually agreed and algorithmically validated for legality (STRAT-008).

## Inputs

Own local position and legal-action set (from C01, via CT-01); opponent's transmitted scent field; incoming verbal hint text; prior belief state.

## Outputs

An emitted scent field (own turn); an updated belief distribution; a selected legal action passed to C04 for orchestration (via `docs/contracts/CT-02-strategy-decision.md`); an outgoing verbal hint.

## Invariants

- Never plants or forges scent at a location not currently occupied (STRAT-004).
- Belief distribution stays normalized over legal cells; see M-02 for the full invariant set.
- Movement selection never depends on an unvalidated LLM output (STRAT-008, NG-003).

## Constraints

- No transport, persistence, or report-sending dependency in this component.
- The verbal-hint provider (if configured) is isolated from movement selection by the same module boundary that satisfies ARCH-007.
- The scent-model abstraction is one small interface with two implementations. Belief and strategy consume the selected profile's output through that boundary and never branch on which model is active; a profile change must not require an edit outside the scent module.

## Failure cases

- Optional provider timeout/429/budget exhaustion: keep the already-selected legal action and fall back to bounded deterministic template text.
- Peer declares a scent model different from ours: refuse to start with a diagnostic and no partial game state, per M-01 §C. A peer that declares nothing is not a mismatch.

## Edge cases

- Repeated emission at the same cell before decay resets it — behavior is the selected profile's (M-01 §B.1 merges by maximum with no upper clamp; §B.2 clamps at `0.9`), and the two genuinely differ. The underlying source question (OPEN-009) stays officially open.
- A hint exceeding the negotiated word limit (STRAT-009 default 15 words).
- Belief mass on a cell that later becomes an impossible cell (barrier placed, or ruled out by new evidence) — must reach zero.

## Acceptance scenarios

- [ ] Mirrors M-01 `{#scent_recurrence}`: the book's multiplicative recurrence is demonstrated by `multiplicative_book_v1` against M-01's non-saturating worked example, while the default `subtractive_chebyshev_v1` intentionally diverges from that decay form and is validated against its own registered vector and the `{#model_lock}` criteria. {#scent_recurrence}
- [ ] Both registered scent profiles are implemented behind one interface, each reproduces its own conformance vector, the default is `subtractive_chebyshev_v1`, and the selected model is declared and compared with the correct refusal behavior. {#model_lock}
- [ ] Belief invariants (normalization, zero mass on impossible/barrier cells, never learns hidden truth) hold under the property tests in M-02. {#belief_invariants}
- [ ] Movement policy always selects from C01's legal-action set; no LLM output can bypass this. {#strategy_legality}

## Relevant contracts

`planning/contracts/CT-01-game-state.md` (consumer); `planning/contracts/CT-02-strategy-decision.md` (owner).

## Relevant OPEN/input gates

- OPEN-009 — officially OPEN, with `implementation_status: OPERATIONAL_CONVENTION`. It does not block `{#model_lock}`: the recorded convention is sufficient to implement, select, declare, and test both models. What still waits on an official answer is the claim that either profile is the correct reading of section 4.3, confirmed before counted play.
- PLANQ-003, PLANQ-004 — team decisions gating whether an optional provider is used at all and what it may generate; `blocks: start` on the optional adapter task only (T027), never on template-mode strategy.

## Definition of Done

All acceptance scenarios pass; the scent module is pure and independent of transport/GUI; belief invariants are property-tested; M-01 and M-02 exist and are cited by name rather than restated; `check_planning_graph.py` shows STRAT-*/ARCH-007 owned only here.
