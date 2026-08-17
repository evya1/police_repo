---
artifact: adr
id: ADR-005
status: accepted
date: 2026-08-17
owners: orchestrator
related_requirements: [NET-001, ARCH-002, ARCH-003]
related_tasks: [T008, T009, T012]
supersedes:
---

# ADR-005 — Shared Protocol Layer Placement in common/transport

Use an ADR only for a sufficiently important and durable technical design decision. Official-input receipt belongs in the Input Register, product/requirement changes belong in a Change Request, and execution work belongs in a task. This decision fixes where the role-agnostic protocol layer lives. It executes an already-approved requirement (the Stage 2 PRD's FR-5) rather than adding, removing, or normatively changing any canonical requirement, so no Change Request applies.

## Context

The Stage 2 shared PRD (`PRD_mcp_infrastructure.md`) makes the protocol layer the project's interoperability boundary: one role-agnostic implementation, deployed byte-identically in both role repositories and parameterized only by `role` (FR-5). Its success criteria make the placement verifiable: SC-6 requires a byte-identical shared layer across the repositories, and the "shared-layer drift = 0 differing files" KPI is measured by the `common/` sync check (TC-24) — a check that is meaningful only for code that actually lives under `common/`.

The repository's own planning artifacts pointed the other way: the C03 PLAN (`docs/components/C03-peer-protocol-integrity/PLAN.md`) implements the transport under `src/<role>_peer/transport/`, and the task write-sets follow it — T009 writes `src/<role>_peer/transport/{mcp_server,mcp_client,contracts}.py`, T012 writes `src/<role>_peer/transport/inbox.py`, T008 writes `src/<role>_peer/integrity/{commit_reveal,audit}.py`. The Stage 2 PRD recorded the discrepancy as open item O-1 and, per the mandatory workflow (guidelines p. 9, §2.5, step 5), the discrepancy had to be reconciled before M2 development proceeds.

The `common/` root already carries byte-identical shared code in both repositories: `common/domain/` (board, rules, scoring) and `common/config/`. A role-local copy of the wire logic would be a private twin that can drift silently — the exact failure mode the referee-less design cannot detect from one side alone.

## Decision

The role-agnostic protocol layer lives in `common/transport/` in this repository and in the sibling repository, byte-identical across the two and parameterized only by `role` and injected configuration. O-1 is resolved in favour of FR-5; FR-5 is not redefined.

- The package holds the wire logic FR-5 assigns to the shared layer: message shapes, negotiation, the inbox, and the server/client adapters. The canonicalization and commit/reveal modules that FR-5 lists in the same role-agnostic layer land under the same shared root; the exact module layout under `common/transport/` is fixed by the C03 PLAN / write-set update (below), not by this ADR.
- Role-specific glue stays in `src/<role>_peer/`: the natural role, the CLI entry, private configuration, strategy wiring, and the thin role-local entry points that instantiate the shared adapters for this peer's role.
- The shared layer stays stateless at module level (SC-6): no module-level mutable state, no network import outside the transport modules, no import of role code. Byte-identical static code in two separate processes with separate configuration areas does not violate ARCH-002/ARCH-003 — it is not shared live memory.
- Mechanical follow-up (orchestrator, pending): the C03 PLAN approach summary and the T009/T012 write-sets (and T008 for the canonicalization/commit-reveal modules) are re-targeted from `src/<role>_peer/` to `common/transport/`; T009's `context_files` gains this ADR. Until that edit lands, the task files' write-set constraints still name the old paths.

## Alternatives considered

- **Keep the protocol layer in `src/<role>_peer/transport/` and redefine FR-5.** Rejected: it would leave a private twin of the wire logic in each role tree, strip the `common/` sync check (SC-6, TC-24) of the subject it exists to check, and contradict both the `common/domain` / `common/config` precedent and the project rule that shared code lives in `common/`. Redefining an approved PRD requirement to fit an execution convenience inverts the authority order.
- **Split the shared layer across several `common/` packages (for example `common/protocol` plus `common/integrity`).** Rejected for now: FR-5 names one role-agnostic protocol layer, and one package keeps the sync-check scope and the "no network import outside the transport modules" source scan simple. Revisit if the package outgrows the per-file line discipline.
- **Move only the server/client adapters to `common/`, leaving negotiation/inbox/audit role-local.** Rejected: FR-5's shared-layer enumeration is explicit, and leaving wire logic role-local reintroduces exactly the drift risk this ADR removes.

## Consequences

- The C03 PLAN and the T009/T012/T008 write-sets need a mechanical re-targeting to `common/transport/` (recorded above). No task is renumbered, split, or dependency-changed; only write-set paths and `context_files` move.
- SC-6 and the drift KPI become checkable end-to-end at Stage 2: the sync check gains its real subject, and TC-24's "0 differing files" applies to the protocol layer.
- Dependency direction stays one-way: `common/transport/` imports no role code; `src/<role>_peer/` imports the shared layer. NFR-5's lazy `fastmcp` import and the 150-line file discipline apply unchanged inside the shared package.
- Negative: a single-repository reader no longer finds the transport under the role tree; the shared code's home is two directories up. Mitigation: the C03 PLAN names the location, the sync check fails loudly on drift, and this ADR records why.

## Validation

- This ADR is byte-identical in the two role repositories (`docs/decisions/`).
- No application source, no `uv.lock`, and no runtime dependency change accompanies this decision; the write-set re-targeting is documentation-only until T008/T009/T012 execute.
- After the write-set update: `scripts/check_planning_graph.py` passes (29 tasks, 6 components, graph unchanged and acyclic) and `scripts/run_quality_gates.py` passes in both repositories, including the Markdown link check.
- At execution time: the `common/` sync check reports 0 differing files across the shared layer (SC-6, TC-24).

## Approval

- Decision owner: orchestrator
- Approved by: project team — orchestrator instruction of 2026-08-17 approving the Stage 2 PRD and fixing the shared protocol layer in `common/transport`
- Approval date: 2026-08-17
