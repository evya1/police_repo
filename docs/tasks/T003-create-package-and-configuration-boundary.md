---
id: T003
status: blocked
priority: P0
implements:
  - ARCH-001
  - ARCH-002
  - ARCH-003
  - ARCH-009
  - CFG-002
  - CFG-003
  - CFG-006
  - CFG-007
  - CFG-008
  - QR-004
  - QR-006
  - QR-012
  - QR-013
depends_on:
  - T002
parallel_safe: false
claimed_by:
claim_expires_at:
write_set:
  - src/police_peer/__init__.py
  - src/police_peer/sdk.py
  - src/police_peer/config/
  - tests/unit/config/
  - tests/unit/test_sdk.py
  - config/repo_quality.toml
  - pyproject.toml
risk: medium
---

# T003 — Create Package And Configuration Boundary

## Expected outcome

A role-local installable package, thin programmatic facade, and validated shared/private configuration boundary exist without shared live state.

## Requirements implemented

- `ARCH-001`
- `ARCH-002`
- `ARCH-003`
- `ARCH-009`
- `CFG-002`
- `CFG-003`
- `CFG-006`
- `CFG-007`
- `CFG-008`
- `QR-004`
- `QR-006`
- `QR-012`
- `QR-013`

## Relevant context

The package is greenfield. Shared JSON overrides conflicting local TOML; validation must distinguish Fixed, Minimum, Negotiated, and private values.

## Constraints

- Do not edit the canonical PRD.
- Do not silently redefine the repository PLAN or task dependencies.
- Do not widen scope or treat a derived design decision as a source requirement.
- Edit only the declared write set; request an orchestrator-approved change before crossing it.
- Escalate requirement conflicts, missing official inputs, and newly discovered work.

## Acceptance criteria

- [ ] The role package imports through one documented programmatic facade.
- [ ] Shared JSON and private TOML load separately, and signed shared values win on conflicts.
- [ ] Known Appendix F defaults and status classes validate with explicit errors.
- [ ] Code/config version compatibility is checked at startup.
- [ ] Tests prove there is no cross-role live-state module or secret-bearing default.
- [ ] Quality/coverage configuration includes the new source package and test paths.

## Verification

- `uv run pytest tests/unit/config tests/unit/test_sdk.py`
- `uv run ruff check src tests/unit/config tests/unit/test_sdk.py`
- `uv run python scripts/run_quality_gates.py`

## Implementation plan

To be completed immediately before execution.

## Handoff contract

Report files changed, tests executed, exact test results, decisions made, deviations, blockers, and newly discovered work. Include command output or artifact paths sufficient for the orchestrator to validate every acceptance criterion.

## Result and evidence
