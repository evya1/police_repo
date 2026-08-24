---
id: T055
status: not_started
priority: P2
task_type: component
component: C06
optional: false
implements:
  - REPORT-005
  - REPORT-006
  - REPORT-007
  - REPORT-008
  - OBS-006
context_files:
  - docs/components/C06-reporting-league/PRD.md
  - docs/components/C06-reporting-league/PLAN.md
  - docs/interop/LEAGUE_COMPATIBILITY.md
  - docs/decisions/ADR-011-league-kit-interoperability-boundary.md
  - docs/spec/OPEN_QUESTIONS.md
read_set:
  - src/police_peer/reporting/replay_bundle.py
  - src/police_peer/reporting/replay_documents.py
  - src/police_peer/reporting/league_kit_projection.py
  - common/transport/league_kit_envelope.py
depends_on:
  - T046
  - T052
  - T053
  - T054
gates: []
parallel_safe: true
claimed_by:
claim_expires_at:
write_set:
  - docs/schema/project_profile/v1/declaration.schema.json
  - docs/schema/project_profile/v1/config.schema.json
  - docs/schema/project_profile/v1/log.schema.json
  - docs/schema/project_profile/v1/result.schema.json
  - docs/schema/project_profile/v1/README.md
  - docs/schema/project_profile/v1/examples/declaration_example.json
  - docs/schema/project_profile/v1/examples/config_example.json
  - docs/schema/project_profile/v1/examples/log_example.json
  - docs/schema/project_profile/v1/examples/result_example.json
  - src/police_peer/reporting/project_schema_projection.py
  - tests/unit/reporting/test_project_schema_projection.py
  - tests/contract/test_project_schema_profile.py
  - docs/inputs/INPUT_REGISTER.md
risk: medium
---

# T055 — Original project-owned schema profile and INPUT-001..006 closure

## Expected outcome

A settled six-sub-game series can be projected into an original, project-owned
`project_schema_profile/v1` JSON Schema contract (declaration, per-sub-game config, per-sub-game
log, result) derived from the book's binding text (SPEC §9.3.3, Appendix B, Appendix F Table 20)
and validated in tests. This is a third, independent artifact projection alongside T046's
`internal_interop` bundle and T053's `kit_interop` projection — it replaces neither and is never
labeled `official_schema`.

## Requirements implemented

- `REPORT-005`…`REPORT-008` — the four official artifact kinds, a shared identifier, repository
  links, per-sub-game commit, and token totals, expressed as an original schema when the lecturer's
  original attachment bytes were not supplied.
- `OBS-006` — schema-validated evidence-projection coverage.

## Relevant context

The project PDF states four example JSON files accompany the book, but their original
attachment bytes were not part of the supplied PDF (`INPUT-001`, `official_status:
MISSING_ORIGINAL_ATTACHMENT`). The user has authorized a project-owned schema for this case. This
task creates that schema from the book's own binding text and the pinned kit contract only where
the book is silent — never from an unrelated repository.

Keep four labels distinct everywhere this task touches: `internal_interop` (T046),
`kit_interop` (T053), `project_schema_profile` (this task), `official_status`
(`MISSING_ORIGINAL_ATTACHMENT`, never rewritten to claim receipt of the original file).

## Constraints

- Edit only the declared write set. Do not modify `T046`'s `replay_bundle.py`/`replay_documents.py`
  or `T053`'s `league_kit_projection.py` — this is an additive, separate projection module.
- Do not import schema, template, or documentation content from any repository other than this
  project and the pinned kit (kit content only for the separate `kit_interop` projection, never
  copied into `project_schema_profile`).
- Deterministic UTF-8 canonical serialization: sorted keys, compact separators,
  `ensure_ascii=False`; reuse the existing canonical-JSON primitive rather than reimplementing it.
- Treat JSON booleans as invalid for every integer-typed field (`additionalProperties: false`
  unless a field is an explicitly documented extension point).
- Never write or imply `official_schema` in code, docstrings, filenames, or emitted artifacts;
  every declaration/config/log/result file and its schema `$id` states
  `schema_profile: "project_schema_profile/v1"` and `official_status:
  "MISSING_ORIGINAL_ATTACHMENT"`.
- Maintain a machine-readable per-field classification of `BOOK_REQUIRED`,
  `KIT_INTEROP_REQUIRED`, or `PROJECT_CONVENTION` in `docs/schema/project_profile/v1/README.md`.

## Acceptance criteria

- [ ] `declaration.schema.json`, `config.schema.json`, `log.schema.json`, `result.schema.json`
      exist under `docs/schema/project_profile/v1/`, each with `$schema`, `$id`, `title`, `type`,
      `required`, `additionalProperties`, and numeric/string constraints.
- [ ] `config.schema.json` requires `schema_version: "1.2"`, `agreed_between`, and the six sections
      `board_and_agents`, `world`, `movement_and_barriers`, `scoring`, `pheromones`,
      `network_and_league`, `rate_limiter_gatekeeper`.
- [ ] `declaration.schema.json` requires stable peer/team identity and role, repository/MCP
      endpoint declarations, hardware/runtime summary without secrets or machine-private paths,
      LLM mode/model/token cap, start/end lifecycle, `game_id`/`game_uid`, sub-game number, config
      digest, code revision, counted/warm-up status, and signing/key identifier or explicit
      unsigned status.
- [ ] `log.schema.json` requires game/sub-game identity, sender/role, ordered step records,
      commit/reveal payload/nonce/commitment, move, redacted hint/discussion, fallback metadata,
      honest token usage, terminal/capture/concession claims, and verdict/coverage kept separate
      from authenticity; forbids secret, raw hidden opponent state, credential, or
      machine-private-path fields.
- [ ] `result.schema.json` requires all six rows in deterministic order, per-row role/outcome/
      score/steps/audit verdict/coverage/code revision, aggregate score and settlement status,
      known-vs-unknown token totals, stable `game_id`/`game_uid`, repository links, evidence member
      references, and a disputed/unsettled representation with no invented winner or sanction.
- [ ] Every example under `examples/` validates against its schema in a test, including one
      Hebrew-plus-emoji field.
- [ ] For a real settled six-sub-game series, `project_schema_projection.py` emits one declaration,
      six configs, six logs, one result (14 files) — proven by an explicit count assertion.
- [ ] One stable `game_id`/`game_uid` across all 14 files, read from the same pinned series
      identity T053 reads, not re-derived independently.
- [ ] Deterministic serialization: re-running the projection over the same settled series produces
      byte-identical output; golden vectors cover key ordering, floats permitted by the game
      config, Unicode, nonces, and IDs.
- [ ] `docs/inputs/INPUT_REGISTER.md` (or the existing open-question register if no separate file
      exists yet) records INPUT-001..006 on the two-axis table from
      `02_SCHEMA_AND_INPUT_RESOLUTION.md`: `official_status` stays `MISSING_ORIGINAL_ATTACHMENT` /
      `NO_COURSE_CREDENTIAL_OBSERVED` / `NO_WRITTEN_CLARIFICATION` / `NO_ORIGINAL_TEMPLATE` as
      applicable; `implementation_status` is `RESOLVED_PROJECT_PROFILE`,
      `EXTERNAL_SUBMISSION_ONLY`, or `RESOLVED_CONSERVATIVE`/`RESOLVED_LOCALLY` as applicable.
  - [ ] No code path after this task has a start-blocking dependency on the unresolved schema
        inputs.
- [ ] No artifact, schema `$id`, docstring, or log line claims `official_schema`.

## Verification

- `uv run pytest tests/unit/reporting/test_project_schema_projection.py tests/contract/test_project_schema_profile.py -v`
- `uv run pytest` (full suite — must remain green)
- `uv run ruff check .`
- `uv run python scripts/check_line_cap.py`
- `uv run python scripts/run_quality_gates.py`

## Handoff contract

Report files changed, tests executed, exact results, INPUT-001..006 table state, decisions,
deviations, and blockers.

## Result and evidence

(to be filled)
