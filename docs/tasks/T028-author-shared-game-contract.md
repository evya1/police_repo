---
id: T028
status: blocked
priority: P0
task_type: component
component: C01
optional: false
implements:
  - CFG-001
  - CFG-009
context_files:
  - docs/components/C01-game-core/PRD.md
  - docs/components/C01-game-core/PLAN.md
read_set: []
depends_on:
  - T003
gates: []
parallel_safe: true
claimed_by:
claim_expires_at:
write_set:
  - config/game.example.json
  - config/game.toml.example
  - config/README.md
risk: medium
---

# T028 — Author The Shared Game Contract

## Expected outcome

A concrete, negotiable `config/game.json` example and a private `config/game.toml.example` exist in the shape fixed by `ADR-001-shared-game-contract-shape.md`, loadable and validated by `T003`'s config boundary, with every value traceable to `docs/spec/CANONICAL_REQUIREMENTS.md`.

## Requirements implemented

- `CFG-001`
- `CFG-009`

## Relevant context

No existing task's write set previously covered `config/game.json` or `config/game.toml` content — `T001` owns official-input intake, `T003` owns the loader/validator code, and this task owns the actual contract file the loader is exercised against. `ADR-001-shared-game-contract-shape.md` records that the nested section layout and its field names are a derived engineering choice, not an official schema; the official schema remains blocked by `OPEN-001`.

## Constraints

- Do not edit the canonical PRD.
- Do not silently redefine the repository PLAN or task dependencies.
- Do not treat this file's shape as an official schema; label every example `EXAMPLE — NOT AN OFFICIAL ATTACHED TEMPLATE` per `config/README.md`.
- Use only the canonical Appendix F key names from `docs/spec/CANONICAL_REQUIREMENTS.md`; never a synonym from a third-party source.
- Edit only the declared write set; request an orchestrator-approved change before crossing it.
- Escalate requirement conflicts, missing official inputs, and newly discovered work.

## Acceptance criteria

- [ ] `config/game.example.json` matches `ADR-001`'s section layout and carries every Fixed/Minimum/Negotiated key from the Appendix F register with its printed default.
- [ ] `network_and_league.num_games` reads `6` (the binding `LEAGUE-001` value), not the non-binding Appendix B example value of `1`.
- [ ] `config/game.toml.example` contains only local-only fields (group identity, network/opponent selection, strategy selection) and no key that could weaken a signed `game.json` value.
- [ ] Loading the example file through `T003`'s validator succeeds with no unrecognized-key or status-violation error.
- [ ] `config/README.md` documents the shape as derived/negotiated, links `ADR-001`, and does not claim official-schema status.
- [ ] No secret, credential, or private identity field appears in either example file.

## Verification

- `uv run pytest tests/unit/config`
- `uv run ruff check config`
- `uv run python scripts/run_quality_gates.py`

## Implementation plan

To be completed immediately before execution.

## Handoff contract

Report files changed, tests executed, exact test results, decisions made, deviations, blockers, and newly discovered work. Include command output or artifact paths sufficient for the orchestrator to validate every acceptance criterion.

## Result and evidence
