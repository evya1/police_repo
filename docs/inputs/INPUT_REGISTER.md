# Official Input Register

This register records the arrival and verification state of authoritative external project inputs. It never stores credential contents, keys, tokens, passwords, private identity data, or other secrets. Record a cryptographic hash only after a non-secret artifact is actually received.

| Input ID | Artifact / Description | Authority | Status | Version / Hash | Date received | Related OPEN IDs | Affected requirements | Notes |
|---|---|---|---|---|---|---|---|---|
| INPUT-001 | Four official JSON templates/schemas for declaration, per-sub-game configuration, log, and result artifacts | Course staff / Moodle | MISSING | — | — | OPEN-001, OPEN-007 | SEC-003; CFG-009, CFG-010; REPORT-005–REPORT-009 | Do not fabricate fields, canonical bytes, or completed match instances. |
| INPUT-002 | Official Moodle Word-to-PDF submission form | Course staff / Moodle | MISSING | — | — | OPEN-002 | SUB-010 | Fill the supplied form without moving or changing fields after receipt. |
| INPUT-003 | Authorized Step 0 signing material and distribution procedure | Course staff | MISSING | — | — | OPEN-006 | SEC-008, SEC-010 | Never record key contents here. A non-secret procedure may be hashed after receipt. |
| INPUT-004 | Clarification of the missing/conflicting report sanction | Course staff | MISSING | — | — | OPEN-004 | REPORT-009 | Record the written answer and its authority; do not infer a sanction. |
| INPUT-005 | Clarification of the “harder” direction for operational Minimum values | Course staff | MISSING | — | — | OPEN-005 | CFG-005, CFG-007 | Defaults remain in force while unresolved. |
| INPUT-006 | Clarification of canonical serialization, signature scope, and identifier relationships not settled by INPUT-001 | Course staff | MISSING | — | — | OPEN-007 | SEC-003; REPORT-005–REPORT-009 | May be superseded by verified official schemas if they fully settle the issue. |
| INPUT-007 | Clarification of game/match/series terminology, role schedule, and tie aggregation | Course staff | MISSING | — | — | OPEN-008 | GAME-013; LEAGUE-001, LEAGUE-006 | Preserve the fixed six-sub-game count and tie value while awaiting semantics. |
| INPUT-008 | Clarification of scent saturation, merge rule, update order, and rounding | Course staff | MISSING | — | — | OPEN-009 | STRAT-003, STRAT-005 | Require a numeric repeated-emission example before the model lock. |
| INPUT-009 | Human-approved public team metadata record | Project team | EXPECTED | — | — | OPEN-003, OPEN-010 | SEC-008; REPORT-007; SUB-002, SUB-003 | Record only publication-intended metadata; exclude legal names and private IDs unless an official private form requires them. |
| INPUT-010 | Verified repository URLs, public MCP endpoints, opponent identifiers, and counted-match agreement | Project team and opponent | EXPECTED | — | — | OPEN-003 | NET-002; REPORT-007, REPORT-008; SUB-002, SUB-003 | Do not record credentials, tokens, or private endpoint secrets. |

## Intake workflow

1. Register the input and set its status to `RECEIVED` without storing secret contents.
2. Verify authority, completeness, version, and any safe hash; then set `VERIFIED` or leave a concrete verification note.
3. Update related `OPEN-*` entries and affected derived artifacts.
4. Open a Change Request only if accepting the verified information materially changes an approved canonical product requirement or PRD contract.
5. Use an ADR for a sufficiently important durable technical decision, and create a new stable task for additional implementation work that does not change product scope.
