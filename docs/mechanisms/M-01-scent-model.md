---
artifact: mechanism-prd
id: M-01
component: C02
status: draft
shared: true
owner: orchestrator
updated: 2026-08-16
---

# M-01 — Scent Model

## Why this mechanism has its own PRD

Both peers must compute byte-identical scent arithmetic independently — a divergence here silently breaks belief maintenance and downstream strategy on both sides with no error either team can detect alone. The recurrence is fully specified, but the repeated-emission/saturation behavior is not (OPEN-009), and the profile reasoning needed to implement safely under that ambiguity would swamp the C02 component PRD.

## Governing requirements

STRAT-002 (emission), STRAT-003 (recurrence + OPEN-009 boundary), STRAT-004 (no forged scent), STRAT-005 (pre-series model lock), CFG-006 (Fixed scent parameters).

---

## A. Official / book requirements (authoritative)

This section states what the project book and the canonical requirement register actually require. Nothing in the implementation-profile sections (B and C) may be presented as the official interpretation of the source where it diverges from the source; where a profile diverges, that divergence is stated plainly rather than hidden.

- On every move or stay, the acting side emits a 5×5 scent field centered on its own cell with fixed center intensity `0.9` and the agreed radial profile (STRAT-002, CFG-006).
- After a full turn by both sides, each scent cell updates by:

  ```
  tau_ij(t+1) = max(0, (1 - 0.10) * tau_ij(t) + delta_tau_ij)
  ```

  where `0.10` is the Fixed decay rate and `delta_tau_ij` is the emission contribution for cell `(i,j)` this turn (STRAT-003, CFG-006).
- A side reads only the opponent's scent field; it never plants or forges scent at a cell it does not occupy (STRAT-004).
- Before a series, both parties exchange the complete emission-and-decay model with a numeric example, confirm identical interpretation, and cryptographically lock the agreement (STRAT-005).

### Decay-form authority — which profile follows the recurrence above

The recurrence above is the **book-side arithmetic**, and its decay is *multiplicative*: `(1 - rho) * tau` with `rho = 0.10`.

- `multiplicative_book_v1` (§B.2) is the supported profile that follows that multiplicative form.
- `subtractive_chebyshev_v1` (§B.1) — our default — **intentionally does not implement that decay form**. It decays subtractively, `round(max(0, tau - 0.1), 3)`. These are two different arithmetic rules, not two spellings of one rule: from `tau = 0.6` with no new deposit, the book form gives `0.6 * 0.9 = 0.54` and the subtractive form gives `0.6 - 0.1 = 0.5`.

The subtractive form is adopted as the project's default interoperability profile. That adoption is an **engineering/operational-convention decision** recorded in `docs/decisions/ADR-004-operational-interoperability-profile.md`. It is **not** a lecturer clarification, it is **not** a resolution of OPEN-009, and it must never be presented as the official reading of the book.

OPEN-009 does not make the decay *form* ambiguous — the book states a multiplicative decay. OPEN-009 concerns upper saturation, repeated emission/merge, deposit-vs-decay order, and rounding, as set out next.

### What is genuinely open (OPEN-009) — still unresolved

Section 4.3 states scent intensity is bounded in `[0, 0.9]`, but no official source states the upper-bound behavior when repeated emission would push a cell above `0.9`: clamp at 0.9, no clamp, additive merge, max-merge, or replace; and no official source fixes whether decay applies before or after a same-turn emission, or how rounding is handled.

`official_status` for OPEN-009 is **OPEN**. Nothing below closes it. Neither profile in section B may be described as the official reading of section 4.3. The pre-counted-play confirmation named in `requirements/OPEN_QUESTIONS.md` still stands.

---

## B. Supported implementation profiles (engineering decision, non-official)

Two profiles are implemented behind one common interface. Both are registered models with pinned parameter documents, so a peer can declare which one it computes and a mismatch is detectable before play rather than mid-game. Selection is an operational convention recorded in `ADR-004` (`docs/decisions/`); it is never a course requirement.

### B.1 Default — `subtractive_chebyshev_v1`

The profile `wire_shape: reference-v3` actually carries, and therefore our default.

| Aspect | Behavior |
|---|---|
| Emission | `half = field_size // 2`; `falloff = emit_intensity / (half + 1)`; for every cell within Chebyshev distance `half` of the emitting cell and inside the board, `value = round(max(0, emit_intensity - falloff * chebyshev_distance), 3)` |
| Emission guard | The field is emitted only when `emit_intensity >= min_center_intensity` |
| Merge | Emitted values merge into the existing field by **maximum** per cell, never by addition |
| Decay | Subtractive: every retained cell becomes `round(max(0, tau - decay_per_step), 3)` |
| Order | **Deposit, then decay** — emit and merge first, decay the whole field afterwards |
| Rounding | Round to 3 decimal places, at both emission and decay |
| Clamp | Lower clamp at `0.0` only; no upper clamp is applied by this profile |
| Cadence | Once per full turn, after both sides have acted |
| Sparse form | Only cells with a value strictly greater than `0` are retained and sent |
| Transport | **Transmitted** — the emitting side sends its own field; the receiver reads the wire value |
| Receiver-side decay | Yes |
| Initial field | Empty |
| Fixed parameters | `field_size = 5`, `emit_intensity = 0.9`, `decay_per_step = 0.1`, `min_center_intensity = 0.5` |
| Conformance vector | `vectors/pheromone.json` (status `CORE`), plus the `subtractive_chebyshev_v1` registration in `vectors/locked_model.json` |

Worked illustration of the transition, from the registered parameter document's own example: a single emission at the center of a 7×7 board yields `0.9` at the center, `0.6` at Chebyshev distance 1, and `0.3` at distance 2; one decay step takes those to `0.8`, `0.5`, and `0.2`.

### B.2 Additional supported — `multiplicative_book_v1`

The verbatim reading of the book's printed figure-4 kernel, kept as the explicit book-oriented alternative. It is **not** deleted or downgraded merely because it is not our default.

| Aspect | Behavior |
|---|---|
| Kernel | The printed 5×5 book figure-4 table, looked up verbatim by `(dr, dc)` offset from the emitting cell — never re-derived from a fitted closed form, because two teams fitting their own Gaussian produce different fields |
| Kernel rows | `(0.04, 0.14, 0.20, 0.14, 0.04)`, `(0.14, 0.42, 0.62, 0.42, 0.14)`, `(0.20, 0.62, 0.90, 0.62, 0.20)`, `(0.14, 0.42, 0.62, 0.42, 0.14)`, `(0.04, 0.14, 0.20, 0.14, 0.04)` |
| Decay | Multiplicative: `(1 - rho) * tau`, with `rho = 0.1` |
| Update | `tau' = clamp((1 - rho) * tau + kernel_delta, 0, center_intensity)` |
| Evaluation order | Exactly `(1 - rho) * tau + delta`, then clamp. The algebraically equivalent `tau - rho * tau + delta` differs in the last bit for many inputs and breaks a byte comparison of two recomputed fields |
| Clamp policy | `[0.0, 0.9]`. The **upper** clamp is not in the book's printed formula, which shows only `max(0, ...)`; the registered profile derives it from the book's own statement that intensity is a continuous value in `[0, 0.9]`. Without it, a decayed cell that takes an adjacent deposit exceeds the center intensity |
| Order | **Decay, then deposit** — the reverse of the reference profile, and one of the two profiles' real divergences |
| Rounding | **None** |
| Cadence | Once per full turn, from an empty start |
| Transport | **Not transmitted** — each side recomputes the rival's field from revealed actions, so there is no receiver-side decay pass |
| Conformance vector | `vectors/scent_book_v3.json` (status `PROMOTED`), plus the `multiplicative_book_v1` registration in `vectors/locked_model.json` |

**Its relationship to the book, stated honestly.** The kernel values are the book's printed values. The multiplicative decay and full-turn cadence follow the book's recurrence directly. The upper clamp, the exact evaluation order, and the no-rounding policy are *interpretation* — the resolution of OPEN-009 in one particular direction, chosen by a third party and reproduced here so the profile is implementable and comparable. None of it is a lecturer clarification, and adopting this profile would not close OPEN-009 either.

### B.3 Divergence between the profiles

The two profiles differ in decay form (subtractive versus multiplicative), update order (deposit-then-decay versus decay-then-deposit), rounding (3 places versus none), upper clamp (absent versus `0.9`), and transport (transmitted versus recomputed). They are not two implementations of one model; they are two models. This is why a peer must declare which it computes, and why both must be implemented and vector-tested rather than one being folded into the other.

---

## C. Selection and lock

- Exactly **one** scent model is selected per compatible pairing. Two peers computing different models cannot agree on a field, and the disagreement is invisible during play.
- Our default selection is `subtractive_chebyshev_v1` (section B.1).
- The selected model is declared through the interoperability contract as a hash over the registered parameter document (see `planning/contracts/CT-03-peer-wire.md`), not as a bare model name and not as a key inside the closed signed-terms set. Hashing a pinned field set is what makes two independent implementations' declarations comparable at all.
- Refusal follows the adopted interop contract: a mismatch fires **only when both peers declare the family and the declared values disagree**. One side declaring while the other is silent is not a mismatch and must not refuse.
- A refused start produces a diagnostic and no partial game state.
- The model selection is a runtime/profile choice read through the existing local (private, non-shared) configuration boundary owned by T003; it is not an Appendix F term and never weakens a signed shared value.

## Numeric worked example — book recurrence only

Explanatory illustration of the section-A multiplicative recurrence. It is **not a conformance vector for either registered implementation profile**, and the `delta = 0.4` deposit below is an arbitrary illustrative number, not a value either profile emits.

Starting from `tau = 0` at a cell one step from center, under the book recurrence in section A alone:

```
t=0: tau = 0.0
t=1 (emission delta = 0.4): tau = max(0, 0.9*0.0 + 0.4) = 0.4
t=2 (no further emission at this cell): tau = max(0, 0.9*0.4 + 0.0) = 0.36
t=3 (no further emission): tau = max(0, 0.9*0.36 + 0.0) = 0.324
```

This traces the book's multiplicative decay and nothing else. `multiplicative_book_v1` follows this decay form; `subtractive_chebyshev_v1` does not, and would take that `0.4` to `0.3` rather than `0.36`. Conformance truth lives in the registered vectors, never in this example:

- `subtractive_chebyshev_v1` — `vectors/pheromone.json`, plus its `vectors/locked_model.json` registration.
- `multiplicative_book_v1` — `vectors/scent_book_v3.json`, plus its `vectors/locked_model.json` registration.

The example also stays well below the `0.9` ceiling, so it says nothing about saturation. Saturating behavior is profile-specific, sits inside OPEN-009, and must be tested against the selected profile's own conformance vector, never asserted as the book's answer.

## Acceptance scenarios

- [ ] The book's multiplicative recurrence is demonstrated by the book-compatible profile: `multiplicative_book_v1` reproduces the non-saturating worked example above to floating-point tolerance. The default `subtractive_chebyshev_v1` intentionally diverges from that decay form and is validated instead against its own registered vector and the `{#model_lock}` criteria below. {#scent_recurrence}
- [ ] Emission never occurs at a cell the emitting side does not occupy. {#no_forged_scent}
- [ ] Both registered profiles are implemented behind one common interface, each reproduces its own conformance vector exactly, and the selected model is declared and compared as a document hash with the correct refusal behavior. {#model_lock}

## Owning task

T005 (`STRAT-002…005, CFG-001, CFG-004`). `{#model_lock}` is no longer gated on an official OPEN-009 answer: the approved profile decision is sufficient to implement, select, and declare a model. OPEN-009 remains officially open and is confirmed before counted play.
