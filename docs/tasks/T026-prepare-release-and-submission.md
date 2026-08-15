---
id: T026
status: blocked
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
  - SUB-008
  - SUB-009
  - SUB-010
  - SUB-011
context_files:
  - docs/PRD.md
  - docs/PLAN.md
read_set: []
depends_on:
  - T020
  - T024
gates:
  - id: INPUT-002
    kind: input
    scope: moodle_form
    blocks: start
  - id: G-TEAM
    kind: input_gate
    scope: public_metadata
    blocks: start
  - id: G-LIVE
    kind: input_gate
    scope: live_endpoints
    blocks: start
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
- `SUB-008`
- `SUB-009`
- `SUB-010`
- `SUB-011`

## Relevant context

Tagging, remote sharing, Moodle submissions, and the official Word-to-PDF form require human authorization and any private identity values must remain outside public repository artifacts.

## Gates

- `INPUT-002` (`input`, `blocks: start`) — this task cannot be claimed until the gate resolves.
- `G-TEAM` (`input_gate`, `blocks: start`) — this task cannot be claimed until the gate resolves.
- `G-LIVE` (`input_gate`, `blocks: start`) — this task cannot be claimed until the gate resolves.

## Constraints

- Do not edit the canonical PRD.
- Do not silently redefine the repository PLAN or task dependencies.
- Do not widen scope or treat a derived design decision as a source requirement.
- Edit only the declared write set; request an orchestrator-approved change before crossing it.
- Escalate requirement conflicts, missing official inputs, and newly discovered work.

## Acceptance criteria

- [ ] The sibling repository link, two Moodle links, and four report links are correct and accessible to authorized reviewers.
- [ ] The repository is public or explicitly shared with the official course address.
- [ ] The official form is filled without moving fields, saved to PDF, and checked by the team.
- [ ] Every member separately submits with the valid eight-character group code; self-grade addresses code quality only.
- [ ] All gates pass at the exact commit tagged and pushed as annotated v1.0-submission.

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
