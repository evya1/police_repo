---
artifact: change-request
id: CR-001
status: approved
date: 2026-08-27
requester: project operator
source_authority: course instructor Yoram Segal
affected_requirements: [LEAGUE-002, LEAGUE-003, LEAGUE-004, REPORT-001, REPORT-009]
affected_prd_sections: [SC-008, C06 observable behavior]
affected_plan_sections: [C06 pairing eligibility]
affected_tasks: [T020]
resulting_prd_version: "0.6"
---

# CR-001 — Separate repeat counted-mode play from official submission eligibility

## Requested change

Permit repeated counted-mode rehearsals against the same opponent while allowing at most one
result per opponent to be officially declared, counted in the league record, and submitted.

## Motivation and evidence

The earlier repository interpretation blocked execution of a second counted-mode series. The
course instructor clarified in writing that teams may play additional counted-mode games against
the same opponent; the restriction applies to which single result is declared and submitted.
INPUT-011 records the clarification relayed by the project operator.

## Source and authority

Course instructor Yoram Segal, via the project operator's 2026-08-27 written clarification.

## Impact

- Behavior and acceptance criteria: repeat counted-mode rehearsals may execute; only one selected result per opponent may enter official reporting.
- Architecture/interfaces: the eligibility boundary moves from series startup to official declaration/submission selection.
- Security/privacy: no change; rehearsals must not contact Gmail.
- Schedule/dependencies/write sets: T020 documentation is superseded in part; code alignment requires separate authorization.
- Tests/docs/submission: pairing-guard tests eventually need to distinguish rehearsal execution from official submission eligibility.
- Compatibility/migration: preserve every existing artifact; repeat runs require isolated roots and may not overwrite or replace the selected result.

## Alternatives

No change would keep the repository stricter than the instructor's rule and incorrectly prevent
permitted rehearsals.

## Approval

- Decision: approved
- Approved by: course instructor clarification, accepted by project operator
- Approval date: 2026-08-27
- Conditions: one official result per opponent; no evidence overwrite; no rehearsal Gmail send.

## Resulting PRD version

- Approved version: 0.6
- Effective date: 2026-08-27

## Required synchronization after approval

- [x] Update affected canonical requirement records.
- [x] Bump the PRD and synchronize both role repositories.
- [x] Update C06 PRD/PLAN coverage.
- [x] Correct T020 documentation and preserve historical analysis with a supersession notice.
- [ ] Align implementation/tests in a separately authorized code task.
