---
artifact: adr
id: ADR-006
status: accepted
date: 2026-08-22
owners: orchestrator
related_requirements: [ARCH-007, STRAT-007, STRAT-008, STRAT-009]
related_tasks: [T007, T021, T037, T038]
supersedes:
---

# ADR-006 — Role Strategy Hard-Constraint Priorities (resolves PLANQ-008 as a team design decision)

Use an ADR only for a sufficiently important and durable technical design decision. This ADR resolves `PLANQ-008` (`docs/spec/OPEN_QUESTIONS.md`, Implementation Decision Register) as an **approved project decision**, not as an official course requirement. It does not create, remove, or reinterpret any canonical requirement; STRAT-007/008/009 and ARCH-007 are unchanged.

## Context

`PLANQ-008` was `TBD_TEAM_DECISION`, blocking T007's `heuristics`-scoped acceptance criterion in both repositories (`blocks: criterion`). Thief-side, most of the movement-selection core already exists (`src/thief_peer/strategy/scoring.py`, `thief.py`, merged via `evya1/thief_repo#36`) but was never checked against an approved priority ordering or required negative-control scenarios. Police-side, `src/police_peer/strategy/{police.py,barriers.py,hints.py,decision.py}` exist on the `police-strategy` branch (PR #34, head `c335818`, itself already past the `5f7c3bf` value this task pack was pinned against) but likewise lack an approved ordering to test against.

## Decision

`PLANQ-008` is resolved with the following priority orderings, binding for T007/T021 seeded-scenario acceptance in both repositories **unless an official/binding spec is later found to conflict**, in which case implementation must stop and escalate rather than override the spec:

**Thief hard constraints, in order:**
1. Legal action only.
2. Never place a barrier (Thief has no barrier action).
3. Avoid a confidently-believed Police cell when another legal cell exists.
4. Avoid trapped/boxed states (no legal move next turn).
5. Then maximize: distance from believed Police position, future mobility, unvisited-cell preference (in that tie-break order).

**Police hard constraints, in order:**
1. Legal action or barrier placement only.
2. Respect the configured barrier quota.
3. Never choose a barrier/route that self-blocks Police's own future legal movement.
4. Process capture responses before selecting the next movement action.
5. Then: pursue the belief peak; place a barrier only when its expected cut/capture value exceeds a configured threshold.

**Required seeded negative controls** (both repositories, `tests/unit/strategy/` and/or `tests/property/strategy/`): an always-STAY opponent scenario, and a disconnected-belief scenario (no reachable belief mass), each with an explicit expected (non-crash, non-illegal-action) outcome.

## Alternatives considered

- **Leave PLANQ-008 unresolved and block T007's `heuristics` criterion indefinitely.** Rejected: blocks W3/W4 completion with no path forward, and the pack's own governance process calls for a team decision, not an official ruling, here.
- **Let each repository choose its own ordering independently.** Rejected: the two roles must be adversarially consistent for KPI/self-play evaluation to mean anything; one ADR, ported byte-identically in spirit (not code) to both repos' decision records, keeps the orderings comparable.

## Consequences

- T007's `heuristics`-scoped acceptance criterion (`{#heuristics}`) in both repositories may now be closed once the seeded scenarios above are demonstrated.
- W3 (thief_repo) and W4 (police_repo) task scope is bounded to: (a) auditing existing strategy code against this ordering, (b) adding the two required negative-control scenarios, (c) documenting any deviation as a finding, not silently reordering weights.
- Does not change `OPEN-011`, `OPEN-004`, or any other OPEN item's official status.

## Validation

- `uv run pytest tests/unit/strategy tests/property/strategy` in each repository, including the two new negative-control scenarios.
- This ADR is byte-identical in `thief_repo` and `police_repo` under `docs/decisions/`.

## Approval

- Decision owner: orchestrator (governance/task-preparation session, 2026-08-22)
- Approved by: project team — recorded per this session's explicit instruction to resolve PLANQ-008 as a team design decision using these recommended priorities
- Approval date: 2026-08-22
