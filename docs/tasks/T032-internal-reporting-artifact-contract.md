---
id: T032
status: done
priority: P0
task_type: component
component: C06
optional: false
implements:
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
gates: []
parallel_safe: true
claimed_by:
claim_expires_at:
write_set:
  - src/police_peer/reporting/schemas.py
  - config/official/reporting/
  - tests/contract/report_schemas/
risk: medium
---

# T032 — Internal Reporting Artifact Contract (NOT OFFICIAL)

## Purpose

This task carries the **project-owned INTERNAL** reporting artifact contract authorized by the
OPEN-001 operational convention (see `docs/spec/OPEN_QUESTIONS.md`), so that the reporting
architecture is buildable and verifiable while the official JSON templates remain missing.

**INTERNAL CONTRACT — NOT OFFICIAL TEMPLATE CONFORMANCE.** This task does NOT adopt official
templates and does not claim they are authentic OPEN-001/INPUT-001 attachments. T016 is complete
under the accepted project schema profile. When authentic official templates arrive, they
replace the project schema at the same boundary (`schemas.py` + `config/official/reporting/`)
without changing the builders, validators, or signing seam.

T032 exists as a separate stable task ID precisely because `T016`'s `blocks: start` gate (INPUT-001)
forbids dispatching official-schema-adoption work, while the operational convention permits the
internal contract now. See the C06 handoff §24 ("T016 governance").

## Requirements carried (INTERNAL contract only — NOT official conformance)

This task carries an INTERNAL project-owned contract. The `implements` IDs are carried as
internal seams; they are NOT marked officially satisfied. Official template conformance stays
gated on INPUT-001/OPEN-001 (carried by official `T016`). Do NOT fabricate official JSON shapes,
filenames, or sanctions.

- `REPORT-005` — internal signed-JSON seam (`sign_artifact`/`verify_artifact`/`serialize`).
- `REPORT-006`/`REPORT-007` — internal deterministic filenames + internal `Declaration` shape
  (substitute; NOT the official four-filename / teams-and-members shape).
- `REPORT-008` — internal `SeriesResult` with repo links, per-sub-game Git commit, and
  per-sub-game + series token totals (internal representation; NOT the official result shape).
- `REPORT-009` — integrated by T018 through mutual result agreement and separate consistent reports.

## Acceptance criteria

- [x] Validators distinguish schema failure (SchemaError), signature failure (SignatureError), and
      cross-artifact identifier mismatch (IdentifierMismatchError).
- [x] Per-game config filenames and reported Git commits are deterministic and replayable
      (`artifact_filename` + `_validate_git_commit`).
- [x] Artifact generation contains only schema-supported fields and no private secrets (recursive
      `_scan_secrets`).
- [x] Builders expose the four lifecycle points without creating a declaration/result prematurely
      or mutating a finalized log (`assert_lifecycle_ok` + `SubGameLog` immutability).
- [x] Test-only candidate layouts are quarantined from production configuration.
- [x] The missing official-template receipt and the accepted project-profile authority/version/hash
      are recorded in the input register through T016.
- [x] Golden tests cover the sanitized project-owned contract without claiming it is an official
      attachment.

## Required fixes from independent review (material — all must be addressed)

An independent DeepSeek V4 Pro review returned `changes_required`. Fix every item below. Make
the SMALLEST correct change per item; do not refactor unrelated code. Edit ONLY files in the
declared write_set. Do NOT modify `docs/tasks/T016-*` or any other task's file — the T016
result/evidence block belongs to `T016`, not this task (write-set attribution).

1. **Finalize-log signing bytes must equal the verified bytes (REPORT-005, blocking).**
   `finalize_log` currently signs the log while `finalized=False`/`signature=None`, then sets
   `signature`/`finalized=True`, so the archived/verified log bytes differ from the signed
   payload. Fix so the stored signature verifies against the FINALIZED log's canonical bytes
   (e.g. set finalized state first, then sign over the finalized canonical bytes, or exclude
   the mutable status fields from the signed canonical form). Add a test that the finalized
   log's stored signature actually verifies against the finalized log.

2. **A finalized log must actually be immutable (blocking).** `SubGameLog.__setattr__` blocks
   `steps/game_id/game_uid/schema_version` but NOT `signature`, and `finalized` can be flipped
   back to `False` to re-enable mutation. Guard `signature` and prevent `finalized` from being
   flipped back to `False` once true (raise on any mutation of a finalized log).

3. **`verify_artifact(..., verifier=None)` must fail coherently.** `sign_artifact` rejects
   `signer=None` (SignatureError); make `verify_artifact` reject `verifier=None` symmetrically
   with a coherent SignatureError rather than silently proceeding.

4. **Tuple/optional type validation must actually work.** `_validate_field_types` only
   handles a single `type` via `isinstance`, so `expected_types["signature"] = (str,
   type(None))` silently matches nothing. Handle a tuple-of-types spec so `(str, type(None))`
   validates correctly.

5. **Required missing fields must fail schema validation.** `_validate_field_types` silently
   skips keys absent from `as_dict()`, so a missing schema field does not raise SchemaError in
   `validate_schema`. Make a required field that is entirely absent fail schema validation.

6. **`SeriesResult` internal contract must represent per-sub-game Git commits and per-sub-game
   token totals where safely derivable (REPORT-008 internal facet).** Add per-sub-game Git
   commit(s) and per-sub-game token totals to the internal `SeriesResult` (internal
   representation, NOT an official shape). Keep `repo_links` and series token totals.

7. **Tests must exercise the real `finalize_log` path and signature verification.**
   `test_artifact_lifecycle.py` finalize-log section never calls `finalize_log` (it manually
   sets `finalized=True` then mutates `steps`; dead `log = log.__class__(**log.as_dict())`
   lines). Replace with a real `finalize_log` call that stores a verifiable signature, then
   assert immutability and that the signature verifies (ties to fix 1/2).

8. **Remove test state pollution / order dependence.** `test_serialization.py` mutates a
   shared fixture in place (`declaration.team = "测试团队"`); use a copy so tests are
   order-independent. `test_validators.py` has a no-op single-artifact `validate_identifiers`
   assertion on an empty/singleton set that asserts nothing consequential — make it assert a
   real outcome or remove it.

After fixes, the targeted contract suite, Ruff, the full pytest suite, the quality gates,
`uv lock --check`, and the write-set audit must all be green.

## Verification

- `uv run pytest tests/contract/report_schemas -q`
- `uv run ruff check src/police_peer/reporting tests/contract/report_schemas`

## Result and evidence

(work populated by the worker/review; police implementation committed on `task/T016-internal-artifact-contract`
@ af4dead and attributed here because the work predates this task ID. See C06 runtime state.)
