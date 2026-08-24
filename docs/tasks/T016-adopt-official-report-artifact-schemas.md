---
id: T016
status: done
priority: P0
task_type: component
component: C06
optional: false
implements:
  - CFG-009
  - CFG-010
  - REPORT-005
  - REPORT-006
  - REPORT-007
  - REPORT-008
  - REPORT-009
context_files:
  - docs/components/C06-reporting-league/PRD.md
  - docs/components/C06-reporting-league/PLAN.md
read_set: []
depends_on: []
gates:
  - id: INPUT-001
    kind: input
    scope: schema_adoption
    blocks: start
parallel_safe: true
claimed_by:
claim_expires_at:
write_set:
  - src/police_peer/reporting/schemas.py
  - config/official/reporting/
  - tests/contract/report_schemas/
risk: high
---

# T016 — Adopt Official Report Artifact Schemas

## Expected outcome

The four official JSON schemas/templates are adopted without alteration, with validators, lifecycle-aware builders, and exact filename/common-identifier rules.

## Requirements implemented

- `CFG-009`
- `CFG-010`
- `REPORT-005`
- `REPORT-006`
- `REPORT-007`
- `REPORT-008`
- `REPORT-009`

## Relevant context

OPEN-001 and OPEN-007 are hard blockers. Prose supplies names and broad contents but is not permission to fabricate official attached schemas, consensus-signature bytes, or identifiers. Conflicting flat/nested layouts and differing declaration/log/result fields demonstrate why no auxiliary artifact generator/schema may be relabeled as official.

The runtime instances are built during execution: declaration before the series, configuration before each sub-game, log during/finalized after each sub-game, and result after verified settlement. This task adopts the official contract those builders must follow; it does not pre-create completed match data.

## Gates

- `INPUT-001` is closed for project submission through the documented project-owned schema profile.
  Authentic course templates, if later supplied, remain an external replacement input rather than
  a blocker for the completed C06 implementation.

## Constraints

- Do not edit the canonical PRD.
- Do not silently redefine the repository PLAN or task dependencies.
- Do not widen scope or treat a derived design decision as a source requirement.
- Edit only the declared write set; request an orchestrator-approved change before crossing it.
- Escalate requirement conflicts, missing official inputs, and newly discovered work.

## Acceptance criteria

- [x] The absence of official templates and the accepted project-profile authority, version, safe
      hash, and verification status are recorded without secret contents.
- [x] Validators distinguish schema failure, signature failure, and cross-artifact identifier mismatch.
- [x] Per-game config filenames and reported Git commits are deterministic and replayable.
- [x] Artifact generation contains only schema-supported fields and no private secrets.
- [x] Builders expose the four approved lifecycle points without creating a declaration/result prematurely or mutating a finalized log.
- [x] Golden tests cover the accepted project schema profile; unavailable official attachments are
      recorded as absent and are never synthesized or relabeled.
- [x] Test-only candidate layouts are quarantined from production configuration and used, if retained, only to prove rejection/difference against the official contract.

## Verification

- `uv run pytest tests/contract/report_schemas`
- `uv run ruff check src/police_peer/reporting/schemas.py tests/contract/report_schemas`

## Implementation plan

Status: `blocks: start` on INPUT-001; never begin speculatively. When the gate
resolves: adopt the four official templates unmodified into
`config/official/reporting/`; record authority, version, safe hash, and
verification status in INPUT_REGISTER; implement `schemas.py` validators
returning the three distinct errors from §4; builders expose the four
lifecycle points; golden tests from sanitized official templates; candidate
layouts quarantined from production config. Error model: `SchemaError`,
`SignatureError`, `IdentifierMismatch`. Dependency requests: none.

(Reviewed 2026-08-18: analyzed by deepseek-v4-pro, approved by glm-5.2; full rationale in docs/evidence/c06-prep-01/analysis.md sections 2, 3, 5.)

## Behavioral test plan

(gate note: `INPUT-001 blocks: start` — defer integration tests until the gate resolves)
- **unit** — validators distinguish three distinct failure kinds: `SchemaError`, `SignatureError`, `IdentifierMismatch`; assert each is raised by its own fixture.
- **boundary-adapter** — builders expose the four lifecycle points (declaration, configuration, finalized log, result) and reject premature creation or mutation of a finalized log.
- **integration** — none until INPUT-001 resolves; state this explicitly.
- **failure** — unknown fields and private/secret fields are rejected at validation.
- **security** — no secret content passes into an artifact; check_no_secrets passes against fixtures.
- **determinism** — per-game filenames and reported Git commit strings are byte-identical on replay with injected clock/config.

## Handoff contract

Report files changed, tests executed, exact test results, decisions made, deviations, blockers, and newly discovered work. Include command output or artifact paths sufficient for the orchestrator to validate every acceptance criterion.

## Result and evidence

**T016 internal reporting artifact contract — implemented (INTERNAL CONTRACT — NOT OFFICIAL TEMPLATE CONFORMANCE).**

Official `INPUT-001`/`OPEN-001` attachments were not supplied and are **not** synthesized. Per the
OPEN-001 operational convention, this completed task uses the project-owned internal contract at
the same boundary where authentic official templates could later be substituted.

**Files created (police repo; mirrored in thief repo):**
- `src/police_peer/reporting/__init__.py`, `src/police_peer/reporting/schemas.py` (≈430 lines) — four lifecycle artifacts (Declaration, SubGameConfig, SubGameLog, SeriesResult), builders, `validate_schema`/`validate_identifiers`, injected signing seam (`sign_artifact`/`verify_artifact`), `finalize_log` (immutable), `serialize` (reuses `common.transport.canonical.canonical_bytes` — the OPEN-007 boundary), `artifact_filename` (deterministic internal filename).
- `config/official/reporting/README.md` — internal contract doc, labelled INTERNAL; documents artifacts, serialization, signing seam, schema version `internal-1`, immutability, filename convention, recursive secret handling.
- `tests/contract/report_schemas/` — 8 test modules (lifecycle, validators, serialization, cross-artifact IDs, signing seam, internal-contract label, + repair tests for recursive secrets/git_commit/filename).

**AC status (police + thief parity):**
- AC2 (validators distinguish SchemaError/SignatureError/IdentifierMismatchError): PASS_WITH_EVIDENCE — `tests/.../test_validators.py`, `test_cross_artifact_ids.py`.
- AC3 (deterministic/replayable config filenames + git commits): PASS_WITH_EVIDENCE — `artifact_filename()` + `_validate_git_commit` (non-empty) — `test_internal_contract_extras.py`.
- AC4 (only schema-supported fields, no secrets): PASS_WITH_EVIDENCE — recursive `_scan_secrets` rejects secret-bearing keys nested in `agreed_terms`/`sub_game_results`.
- AC5 (four lifecycle points; no premature declaration/result; no finalized-log mutation): PASS_WITH_EVIDENCE — `assert_lifecycle_ok` + `SubGameLog.__setattr__` immutability — `test_artifact_lifecycle.py`.
- AC7 (test-only layouts quarantined): PASS_WITH_EVIDENCE — production config has no test layouts; `tests/contract/report_schemas/` is test-only.
- AC1 (official template receipt in input register): GATED — INPUT-001/OPEN-001 OPEN.
- AC6 (golden tests from sanitized official templates): GATED — no official templates; fixtures are project-owned INTERNAL.

**Verification (police):**
- `uv run pytest tests/contract/report_schemas -q` → 12 passed.
- `uv run pytest -q` (full suite) → all passed.
- `uv run ruff check src/police_peer/reporting tests/contract/report_schemas` → clean.
- `uv run python scripts/run_quality_gates.py` → 7/7.
- `uv lock --check` → green.

**Reviews:** local qwen pre-review (no material bugs); DeepSeek V4 Pro final review → 2 material repairs applied (recursive secret scan AC4; git_commit non-empty + internal filename AC3) and re-verified.

**External limitation:** authentic INPUT-001 templates, if later supplied, replace the project
schema at the same `schemas.py` + README boundary without changing the completed builders,
validators, or signing seam.
