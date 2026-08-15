---
id: T003
status: blocked
priority: P0
task_type: foundation
component: C01
optional: false
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
context_files:
  - docs/components/C01-game-core/PRD.md
  - docs/components/C01-game-core/PLAN.md
read_set: []
depends_on:
  - T002
gates: []
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

## Configuration test vectors

The contract shape validated here is `ADR-001-shared-game-contract-shape.md`; do not hardcode its example values as alternatives to Appendix F, and reject any key not in the canonical register (`docs/spec/CANONICAL_REQUIREMENTS.md` CFG-006–CFG-008).

| Vector | Input | Expected |
|---|---|---|
| Minimum status, at floor | `grid_size = 7` | accept |
| Minimum status, below floor | `grid_size = 6` | reject, names `grid_size` |
| Minimum status, raised by agreement | `grid_size = 8` | accept |
| Minimum status, below floor | `max_barriers = 10`, `survival_threshold = 30` | reject, names the offending key |
| Fixed status, unchanged | `move_set = ["N","S","E","W","STAY"]` | accept |
| Fixed status, changed | `move_set` reordered or shortened | reject (Fixed is immutable) |
| Fixed status, changed | `capture_cop`, `capture_thief`, `survival_cop`, `survival_thief`, `tie_score` altered | reject (Fixed is immutable) |
| Negotiated status, no agreement | `axis_origin_corner` absent | default `top-left` applies |
| Negotiated status, agreed | `axis_origin_corner = "bottom-right"`, identical at both peers | accept |
| Renamed/unknown key | any key not in the canonical register (e.g. `board_size` instead of `grid_size`) | reject, names the unrecognized key |
| Shared/private precedence | `game.toml` sets a key also present in `game.json` | signed JSON value wins; TOML value discarded |
| Shared/private precedence, weakening attempt | `game.toml` sets a Minimum key below the signed JSON value | reject; TOML cannot weaken a signed condition |
| Missing section | any Appendix-F-covered section entirely absent | reject, names the missing section |

## Implementation plan

To be completed immediately before execution.

## Handoff contract

Report files changed, tests executed, exact test results, decisions made, deviations, blockers, and newly discovered work. Include command output or artifact paths sufficient for the orchestrator to validate every acceptance criterion.

## Result and evidence
