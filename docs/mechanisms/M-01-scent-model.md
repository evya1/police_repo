---
artifact: mechanism-prd
id: M-01
component: C02
status: draft
shared: true
owner: orchestrator
updated: 2026-08-15
---

# M-01 — Scent Model

## Why this mechanism has its own PRD

Both peers must compute byte-identical scent arithmetic independently — a divergence here silently breaks belief maintenance and downstream strategy on both sides with no error either team can detect alone. The recurrence is fully specified, but the repeated-emission/saturation behavior is not (OPEN-009), and the compatibility-matrix reasoning needed to test that safely would swamp the C02 component PRD.

## Governing requirements

STRAT-002 (emission), STRAT-003 (recurrence + OPEN-009 boundary), STRAT-004 (no forged scent), STRAT-005 (pre-series model lock), CFG-006 (Fixed scent parameters).

## Specified behavior (binding)

- On every move or stay, the acting side emits a 5×5 scent field centered on its own cell with fixed center intensity `0.9` and the agreed radial profile (STRAT-002, CFG-006).
- After a full turn by both sides, each scent cell updates by:

  ```
  tau_ij(t+1) = max(0, (1 - 0.10) * tau_ij(t) + delta_tau_ij)
  ```

  where `0.10` is the Fixed decay rate and `delta_tau_ij` is the emission contribution for cell `(i,j)` this turn (STRAT-003, CFG-006).
- A side reads only the opponent's transmitted scent field; it never plants or forges scent at a cell it does not occupy (STRAT-004).
- Before a series, both parties exchange the complete emission-and-decay model with a numeric example, confirm identical interpretation, and cryptographically lock the agreement (STRAT-005).

## What is genuinely open (OPEN-009)

Section 4.3 states scent intensity is bounded in `[0, 0.9]`, but no source states the upper-bound behavior when repeated emission would push a cell above `0.9`: clamp at 0.9, no clamp, additive merge, max-merge, or replace; and no source fixes whether decay applies before or after a same-turn emission, or how rounding is handled.

## Numeric worked example (non-saturating, for test-vector construction)

Starting from `tau = 0` at a cell one step from center (illustrative — a full 5×5 profile and center-cell value are defined in the locked model, not invented here):

```
t=0: tau = 0.0
t=1 (emission delta = 0.4): tau = max(0, 0.9*0.0 + 0.4) = 0.4
t=2 (no further emission at this cell): tau = max(0, 0.9*0.4 + 0.0) = 0.36
t=3 (no further emission): tau = max(0, 0.9*0.36 + 0.0) = 0.324
```

This example is safe to test today because it never approaches the `0.9` ceiling. A worked example that does approach or exceed `0.9` must not select a saturation behavior in advance of the lock.

## Compatibility decision matrix (differential tests only — not a default)

| Axis | Candidates | Selection gate |
|---|---|---|
| Ceiling handling | clamp at 0.9 · no clamp · replace at ceiling | OPEN-009 lecturer confirmation |
| Repeated-emission merge | additive · max · replace | OPEN-009 |
| Update order | decay-then-emit · emit-then-decay | OPEN-009 |
| Rounding | truncate · round-half-even · exact rational | OPEN-009 |
| Transmitted vs. recomputed field | trust wire value · recompute locally and compare | OPEN-009, SEC-003 (canonical bytes) |

## Acceptance scenarios

- [ ] The non-saturating recurrence matches the worked example above to floating-point tolerance. {#scent_recurrence}
- [ ] Emission never occurs at a cell the emitting side does not occupy. {#no_forged_scent}
- [ ] All five compatibility-matrix axes are exercised as differential tests, and none is selected as a production default before the lock. {#model_lock}

## Owning task

T005 (`STRAT-002…005, CFG-001, CFG-004`), with the lock criterion gated by OPEN-009 at `{#model_lock}` only.
