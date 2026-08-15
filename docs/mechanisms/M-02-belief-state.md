---
artifact: mechanism-prd
id: M-02
component: C02
status: draft
shared: true
owner: orchestrator
updated: 2026-08-15
---

# M-02 — Belief State

## Why this mechanism has its own PRD

The belief update is a probabilistic algorithm with hard invariants that two other components depend on directly — C05's heatmap renders it verbatim, and T021's property tests assert its bounds independently of any specific strategy. Documenting the invariants once, here, means C05 and the test suite never need to read C02's PLAN internals.

## Governing requirements

STRAT-001 (own-position-only knowledge, opponent belief map), STRAT-006 (belief updates materially influence legal move selection).

## Specified behavior (binding)

- Each side knows only its own position; it receives the opponent's transmitted scent field and any hint text, and maintains a probabilistic belief distribution over the opponent's possible location (STRAT-001).
- The belief map is updated from scent and hints after each turn, and the updated belief materially influences legal move selection for both roles (STRAT-006) — belief is not cosmetic.

## Invariants (binding regardless of the specific update algorithm chosen)

1. **Normalization**: the belief distribution sums to 1 over all cells at every point after initialization.
2. **Impossible-cell exclusion**: a cell known to be a barrier, or otherwise ruled out by local evidence (e.g. this role's own position, if mutually exclusive), carries zero probability mass, and mass removed from an excluded cell is redistributed rather than lost.
3. **No hidden-truth leakage**: the belief update never reads the opponent's actual position; it is inference over scent and hints only (derived from ARCH-003, STRAT-001, OBS-002).
4. **Monotonic evidence incorporation**: a new scent reading or hint updates the distribution; it is never silently discarded once received.

## Inputs

Prior belief distribution; the transmitted opponent scent field (M-01's output); an incoming hint (natural-language, per NET-003).

## Outputs

An updated belief distribution, consumed by C05's heatmap (OBS-003) and by the role-specific strategy mechanism (M-03/M-04) for legal move selection.

## Edge cases

- First turn: no prior evidence — the initial distribution must still satisfy invariant 1, uniformly over legal cells or however the component PLAN defines it.
- A hint that is deceptive (permitted by STRAT-009) but not distinguishable from a truthful one by the belief update alone — the invariant is about the belief's internal consistency, not about detecting deception.
- A barrier newly declared this turn removing probability mass from a previously-uncertain cell.

## Acceptance scenarios

- [ ] The belief distribution is normalized after every update in the property-test suite. {#belief_normalized}
- [ ] Zero probability mass exists on any impossible or barrier cell after the update that ruled it out. {#belief_impossible_cells}
- [ ] No belief-update code path reads a value only available from objective opponent state. {#belief_no_leak}

## Owning task

T006 (`STRAT-001, STRAT-006`), depends on T005 (scent).
