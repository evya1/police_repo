---
id: T020
status: done
priority: P0
task_type: component
component: C06
optional: false
implements:
  - LEAGUE-002
  - LEAGUE-003
  - LEAGUE-004
  - LEAGUE-007
context_files:
  - docs/components/C06-reporting-league/PRD.md
  - docs/components/C06-reporting-league/PLAN.md
read_set: []
depends_on:
  - T018
  - T019
gates:
  - id: G-LIVE
    kind: input_gate
    scope: pairing_preflight
    blocks: criterion
parallel_safe: true
claimed_by:
claim_expires_at:
write_set:
  - src/police_peer/league/preflight.py
  - tests/unit/league/test_pairing_guards.py
  - tests/integration/test_preflight.py
risk: high
---

# T020 — Implement League Pairing Guards

> **Authoritative correction (2026-08-27):** INPUT-011/CR-001 supersedes the original
> per-opponent play prohibition below. Repeat counted-mode rehearsals may execute against the
> same opponent; the guard belongs at official declaration/submission and permits only one
> selected result per opponent. The existing implementation remains stricter and needs a
> separately authorized code-alignment task; this documentation update does not change code.

## Expected outcome

Preflight guards enforce counted-match eligibility and truthful declarations, while preserving auditable evidence for computational fairness.

## Requirements implemented

- `LEAGUE-002`
- `LEAGUE-003`
- `LEAGUE-004`
- `LEAGUE-007`

## Relevant context

The system reports required inputs but never invents lecturer-side normalization. Warm-ups remain explicitly non-counted.

## Gates

- `G-LIVE` was exercised by the preserved real match. The production preflight, counted/warm-up
  separation, opponent-history limits, declarations, and evidence checks are accepted as complete.

## Constraints

- Do not edit the canonical PRD.
- Do not silently redefine the repository PLAN or task dependencies.
- Do not widen scope or treat a derived design decision as a source requirement.
- Edit only the declared write set; request an orchestrator-approved change before crossing it.
- Escalate requirement conflicts, missing official inputs, and newly discovered work.

## Acceptance criteria

- [ ] The peer permits isolated repeat counted-mode rehearsals but refuses an eleventh officially submitted result or a second official declaration/submission for the same opponent.
- [x] At least two distinct opponents is tracked as a submission obligation, not faked before completion.
- [x] Prior counted-match declarations are signed, compared, and retained.
- [x] Warm-up and counted modes are unambiguous and cannot share report state accidentally.
- [x] Hardware/code/token evidence is complete but contains no local fairness score formula.
- [x] Preflight eligibility, declaration, and endpoint checks pass against real opponent/endpoint data once `G-LIVE` is satisfied. `{#pairing_preflight}`

## Verification

- `uv run pytest tests/unit/league/test_pairing_guards.py tests/integration/test_preflight.py`
- `uv run ruff check src/police_peer/league/preflight.py tests/unit/league/test_pairing_guards.py tests/integration/test_preflight.py`

## Implementation plan

`preflight.py` is intended to provide pure guards over opponent history and signed
declarations: enforce 2..10 officially submitted results total (LEAGUE-002), at most one
officially declared/submitted result per opponent while permitting isolated repeat counted-mode
rehearsals (LEAGUE-003), truthful prior-count declarations
signed/compared/retained (LEAGUE-004), warm-up/counted mode separation, and
hardware/version/token evidence collection with **no** local normalization
formula (LEAGUE-007). Live endpoint checks are behind the G-LIVE criterion
and must fail closed until real opponent/endpoint data is present. Error
model: `TooManyCountedMatches`, `DuplicateOpponent`, `DeclarationMismatch`.

(Reviewed 2026-08-18: analyzed by deepseek-v4-pro, approved by glm-5.2; full rationale in docs/evidence/c06-prep-01/analysis.md sections 2, 3, 5.)

## Behavioral test plan

(gate note: `G-LIVE blocks: criterion` on `pairing_preflight` — live endpoint checks wait)
- **unit (guards)** — allow a repeat counted-mode rehearsal; refuse an eleventh official submission and a second official submission against the same opponent; warm-up, rehearsal, and official report state remain isolated.
- **unit (declarations)** — signed prior counted-match declarations are compared and retained.
- **integration** — preflight pass/fail cases run against synthetic double data; live endpoint data required only for the G-LIVE criterion.
- **failure** — a false prior-match declaration returns the LEAGUE-004 disqualification verdict.
- **security** — hardware/version/token evidence is complete and contains no local fairness-score formula computation (LEAGUE-007).
- **determinism** — identical opponent history yields an identical eligibility verdict.

## Handoff contract

Report files changed, tests executed, exact test results, decisions made, deviations, blockers, and newly discovered work. Include command output or artifact paths sufficient for the orchestrator to validate every acceptance criterion.

## Result and evidence

Completed on `production-fixes` under the earlier interpretation. INPUT-011/CR-001 later narrowed
the per-opponent limit to official declaration/submission rather than execution. The existing guard
therefore remains over-restrictive until a separately authorized code-alignment task lands. Its
prior declaration retention and incomplete-evidence failures remain valid.
