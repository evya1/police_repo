---
artifact: component-plan
id: PLAN-C06-POLICE
component: C06
status: draft — architecture reviewed 2026-08-18; OPEN-001/004/008 official inputs still pending
derived_from: PRD-C06
owner: orchestrator
updated: 2026-08-18
---

# C06 — Reporting & League (Police PLAN)

**Architecture is now reviewed** (T030 preparation pass, 2026-08-18); the
remaining depth gap is entirely upstream — C06's schema and sanction detail
still depends on OPEN-001/004/008, none of which is expected to resolve
before C01–C03 complete.

## Purpose (repeated from the component PRD for orientation)

`src/police_peer/reporting/` — official artifact schemas (once OPEN-001 resolves), the reconciliation/settlement algorithm (M-07), and the send-only Gmail pipeline. `src/police_peer/league/` — series/scoring/pairing-eligibility. `src/police_peer/infra/external_api_gatekeeper.py` — the single external-service Gatekeeper (also used by the optional T027 provider).

## What is fixed now

- Owns REPORT-001…013, LEAGUE-001…007, QR-008, QR-018.
- INPUT-011/CR-001 pins LEAGUE-003 at the declaration/submission boundary: repeat counted-mode rehearsals may execute, but only one isolated result per opponent may enter the official record.
- Consumes CT-04 (canonical bytes, non-official draft) and CT-06 (verified sub-game result); never recomputes either.
- M-07's reconciliation algorithm shape (independent derivation → cross-check against peer draft → refuse silent auto-resolution on mismatch) is binding now even though the sanction/tie-aggregation values it plugs into are not.

## What T016–T020 will author here when claimed

Exact artifact-schema module once OPEN-001 resolves; Gatekeeper rate-limit/DOS/backoff/quota implementation; series/scoring module layout; pairing-preflight checklist implementation.

## Architecture (reviewed 2026-08-18, T030 preparation pass)

Analyzed by deepseek-v4-pro, approved by glm-5.2. Module-level detail (error
models, resource lifecycle, dependency requests) is authored in each task's
own `## Implementation plan`; full rationale in
`docs/evidence/c06-prep-01/analysis.md`.

### PY profile and module boundaries

**Profile: `PY-2`.** Reason (verbatim): "C06 contains real stakeholder-facing
business rules — the fixed GAME-013 score table, the six-sub-game invariant
(LEAGUE-001), pairing-eligibility guards (LEAGUE-002/003/004), the diversity
reward (LEAGUE-005), and the M-07 reconciliation algorithm — plus mandated
external I/O (Gmail through the Gatekeeper). That is the PY-2 case of one
maintained application with business rules and external I/O. PY-1 is
insufficient because the component is not a CRUD/data pipeline; PY-3 is
unnecessary because the domain state is derived immutable result records and
the only concurrency is a token-bucket limiter, not business transactions."

**Module boundaries (paths already owned by T016–T020 write sets):**
- `src/police_peer/reporting/schemas.py` — T016 (only after INPUT-001 resolves).
- `config/official/reporting/` — T016 (adopted official templates + sanitized golden fixtures).
- `src/police_peer/infra/external_api_gatekeeper.py` — T017 (the single external-service Gatekeeper, QR-008).
- `src/police_peer/reporting/gmail.py` — T017 (Gmail adapter behind the send seam).
- `src/police_peer/reporting/pipeline.py` + `src/police_peer/reporting/artifacts.py` — T018 (lifecycle orchestration + artifact builders/signers).
- `src/police_peer/league/series.py` + `src/police_peer/league/scoring.py` — T019 (pure deterministic functions).
- `src/police_peer/league/preflight.py` — T020 (pairing-eligibility guards).

**Dependency direction (exact):** `league` imports nothing from `reporting`;
`reporting` consumes `league.scoring` totals ONLY via the CT-06 verified-result
record and never recomputes them; `reporting` and any future provider adapter
depend on `infra.external_api_gatekeeper`; `infra` knows no product types. No
circular imports.

**Side-effect boundary (exact):** the only side-effectful boundary is
`infra.external_api_gatekeeper` plus the injected Gmail send seam; everything
else is pure and deterministic. Live OAuth/send is human-gated and
structurally absent from tests.

**QR-008 conformance (exact sentence):** "Every external-service call in C06
passes through `external_api_gatekeeper.py`; no reporting, league, or
strategy module may import or construct a Google client, and direct service
calls are structurally prevented by the narrow send seam."

### Pattern verdicts

| Pattern | Verdict | Concrete reason tied to C06 |
|---|---|---|
| Repository | DO_NOT_USE | Artifacts are derived in-memory from verified CT-06 results; no persistent data-store abstraction exists, and adding one is speculative. |
| Unit of Work | DO_NOT_USE | No transactional multi-aggregate writes; M-07 reconciliation is a comparison algorithm, not a transaction boundary. |
| Service Layer | USE | `reporting/pipeline.py` is the one application use-case (settle → build → send), implemented as plain orchestration functions, not a class hierarchy. |
| rich Domain Model | DO_NOT_USE | Scoring/series are pure deterministic functions over immutable result records; no entity lifecycles warrant a rich object model. |
| Protocol | USE | Narrow `Protocol`/`Callable` seams (send seam, limiter, clock) compose dependencies manually per AGENTS.md; no DI container. |
| Adapter | USE | `reporting/gmail.py` adapts the protocol to Google's API; the OPEN-007 canonical serializer is an adapter at the byte boundary. |
| Aggregate | DO_NOT_USE | The "verified result is terminal" invariant is enforced by pure validation functions, not a cluster-of-entities root. |
| Message Bus | DO_NOT_USE | No in-process event propagation; synchronous pipeline calls suffice. |
| CQRS | DO_NOT_USE | Read and write workloads are identical (derive totals, write the report); splitting them adds cost with no benefit. |
| Event Sourcing | DO_NOT_USE | Replay of step logs is C05's concern; C06 consumes CT-06 final verdicts and never reconstructs state from an event stream. |

## Known risks (fixed now, detail deferred)

Building a full schema implementation against a guessed OPEN-001 shape (prohibited by NG-004) — mitigated by keeping T016 gated `blocks: start` on OPEN-001/INPUT-001 rather than proceeding speculatively.
