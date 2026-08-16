# Official Input Register

This register records the arrival and verification state of authoritative external project inputs. It never stores credential contents, keys, tokens, passwords, private identity data, or other secrets. Record a cryptographic hash only after a non-secret artifact is actually received.

The `Gate` column names the input-gate class defined in `OPEN_QUESTIONS.md` that this input satisfies. Tasks cite the gate `id`, never a composite string, in their `gates:` frontmatter entries.

| Input ID | Artifact / Description | Authority | Status | Version / Hash | Date received | Related OPEN IDs | Affected requirements | Gate | Notes |
|---|---|---|---|---|---|---|---|---|---|
| INPUT-001 | Four official JSON templates/schemas for declaration, per-sub-game configuration, log, and result artifacts | Course staff | MISSING | — | — | OPEN-001, OPEN-007 | SEC-003; CFG-009, CFG-010; REPORT-005–REPORT-009 | G-OFFICIAL | Do not present a locally defined field contract, canonical byte rule, or completed match instance as official. Development proceeds against the project artifact contract recorded under OPEN-001. |
| INPUT-002 | Official Word-to-PDF submission form | Course staff | MISSING | — | — | OPEN-002 | SUB-010 | G-OFFICIAL | Fill the supplied form without moving or changing fields after receipt. |
| INPUT-003 | Answer on whether Step 0 requires a course-supplied credential, and its distribution procedure if one exists | Course staff | MISSING | — | — | OPEN-006 | SEC-008, SEC-010 | G-OFFICIAL | No such credential is known to exist and none may be assumed. Never record key contents here. A non-secret procedure may be hashed after receipt. Step 0 is implemented against the documented project mechanism with an injected credential seam. |
| INPUT-004 | Clarification of the missing/conflicting report sanction | Course staff | MISSING | — | — | OPEN-004 | REPORT-009 | G-OFFICIAL | Record the written answer and its authority; do not infer a sanction. The conservative settlement guard under OPEN-004 applies meanwhile. |
| INPUT-005 | Clarification of the "harder" direction for operational Minimum values | Course staff | MISSING | — | — | OPEN-005 | CFG-005, CFG-007 | G-OFFICIAL | Defaults remain in force while unresolved. See the OPEN-005 local resolution in `OPEN_QUESTIONS.md`: the enforceable floor and agreement rules are already determined; only the descriptive label is missing. |
| INPUT-006 | Clarification of canonical serialization, signature scope, and identifier relationships not settled by INPUT-001 | Course staff | MISSING | — | — | OPEN-007 | SEC-003; REPORT-005–REPORT-009 | G-OFFICIAL | May be superseded by verified official schemas if they fully settle the issue. The recorded canonical serialization convention governs implementation meanwhile. |
| INPUT-007 | Clarification of game/match/series terminology, role schedule, and tie aggregation | Course staff | MISSING | — | — | OPEN-008 | GAME-013; LEAGUE-001, LEAGUE-006 | G-OFFICIAL | Preserve the fixed six-sub-game count and tie value while awaiting semantics. |
| INPUT-008 | Clarification of scent saturation, merge rule, update order, and rounding | Course staff | MISSING | — | — | OPEN-009 | STRAT-003, STRAT-005 | G-OFFICIAL | Require a numeric repeated-emission example before confirming the locked model for counted play. |
| INPUT-009 | Human-approved team, runtime, and submission metadata record | Project team | EXPECTED | — | — | OPEN-003, OPEN-010 | SEC-008; REPORT-007; SUB-002, SUB-003 | G-TEAM | Confirms team name, team number, GitHub handles, group code, repository URLs, and the declared hardware/model fields. Exclude legal names and private identifiers unless an official private form requires them. |
| INPUT-010 | Verified public MCP endpoints, tunnel procedure, opponent identifiers, and counted-match agreement | Project team and opponent | EXPECTED | — | — | OPEN-003 | NET-002; REPORT-007, REPORT-008; SUB-002, SUB-003 | G-LIVE | Live values only; none may be invented. Do not record credentials, tokens, or private endpoint secrets. |
| INPUT-011 | Clarification of move-cap-versus-survival-threshold termination and round-versus-half-turn step counting | Course staff | MISSING | — | — | OPEN-011 | GAME-013, GAME-014, CFG-007 | G-OFFICIAL | Neither value may be inferred from any non-authoritative material; retain both binding minimums of 35 while unresolved. |

## Intake workflow

1. Register the input and set its status to `RECEIVED` without storing secret contents.
2. Verify authority, completeness, version, and any safe hash; then set `VERIFIED` or leave a concrete verification note.
3. Update related `OPEN-*` entries and affected derived artifacts.
4. Open a Change Request only if accepting the verified information materially changes an approved canonical product requirement or PRD contract.
5. Use an ADR for a sufficiently important durable technical decision, and create a new stable task for additional implementation work that does not change product scope.

## What this register does not hold

Only authoritative course inputs are registered here. An operational convention recorded in `OPEN_QUESTIONS.md` or an ADR is a project decision, not an input, and is never given a row in this table regardless of how much implementation depends on it. Supporting technical material of any kind is likewise not an official input and does not close an `OPEN-*` item.
