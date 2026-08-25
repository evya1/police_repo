---
id: T026
status: done
priority: P0
task_type: release
component: system
optional: false
implements:
  - SUB-001
  - SUB-002
  - SUB-003
  - SUB-004
  - SUB-005
  - SUB-006
  - SUB-007
  - SUB-009
  - SUB-011
context_files:
  - docs/PRD.md
  - docs/PLAN.md
read_set: []
depends_on:
  - T020
  - T024
gates: []
parallel_safe: false
claimed_by:
claim_expires_at:
write_set:
  - docs/evidence/submission-checklist.md
risk: high
---

# T026 — Prepare Release And Submission

## Expected outcome

The reviewed repository and official submission artifacts are frozen at annotated tag v1.0-submission and all human submission/share gates are recorded.

## Requirements implemented

- `SUB-001`
- `SUB-002`
- `SUB-003`
- `SUB-004`
- `SUB-005`
- `SUB-006`
- `SUB-007`
- `SUB-009`
- `SUB-011`

## Relevant context

Tagging and remote sharing require human authorization, and private identity values must remain outside public repository artifacts.

## Gates

Team metadata and live-match evidence are resolved: group code `ZeroOne0` is confirmed and the counted external series is complete.

## Constraints

- Do not edit the canonical PRD.
- Do not silently redefine the repository PLAN or task dependencies.
- Do not widen scope or treat a derived design decision as a source requirement.
- Edit only the declared write set; request an orchestrator-approved change before crossing it.
- Escalate requirement conflicts, missing official inputs, and newly discovered work.

## Acceptance criteria

- [x] The sibling repository link and report/evidence links are correct and accessible to authorized reviewers.
- [x] The repository is public.
- [x] All gates pass at the exact commit frozen by annotated `v1.0-submission`.

## Verification

- `uv run ruff check .`
- `uv run pytest`
- `uv run python scripts/run_quality_gates.py`
- `git show-ref --tags --verify refs/tags/v1.0-submission`
- `git cat-file -t v1.0-submission`

## Implementation plan

To be completed immediately before execution.

## Handoff contract

Report files changed, tests executed, exact test results, decisions made, deviations, blockers, and newly discovered work. Include command output or artifact paths sufficient for the orchestrator to validate every acceptance criterion.

## Result and evidence

Complete. The [submission checklist](../evidence/submission-checklist.md) records the public repository, sibling link, completed match, GUI proof, verified commands, normal merge, and annotated release tag.
