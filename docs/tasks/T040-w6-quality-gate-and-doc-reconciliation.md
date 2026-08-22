---
id: T040
status: ready
priority: P0
task_type: governance
component: C06
optional: false
implements: []
context_files:
  - config/repo_quality.toml
  - scripts/check_line_cap.py
  - scripts/check_planning_graph.py
read_set:
  - docs/tasks/
  - docs/TODO.md
  - README.md
depends_on: []
gates: []
parallel_safe: true
claimed_by:
claim_expires_at:
write_set:
  - config/repo_quality.toml
  - docs/tasks/T009-define-mcp-contract-and-peer-adapters.md
  - docs/tasks/T030-port-fsm-alternative-driver.md
  - docs/tasks/T016-adopt-official-report-artifact-schemas.md
  - docs/tasks/T032-internal-reporting-artifact-contract.md
  - docs/tasks/T007-extend-kpi-harness.md
  - docs/tasks/T007-extend-wire-brain-swap.md
  - docs/TODO.md
  - README.md
risk: low
---

# T040 — Wave W6: Quality-Gate / Module-Size and Documentation Reconciliation (police_repo)

## Purpose

Fix the governance/tooling-visible defects found during the 2026-08-22 governance pass.

## Findings from this session (verified by running the checkers, not assumed)

1. `config/repo_quality.toml` has `source_dirs = []` — same defect as thief_repo. Running
   `scripts/check_line_cap.py src common` directly found **6 files already over the
   150-logical-line limit**:
   - `src/police_peer/reporting/schemas.py` — 448 lines
   - `common/config/__init__.py` — 267 lines
   - `common/transport/negotiate.py` — 196 lines
   - `common/transport/series.py` — 172 lines
   - `src/police_peer/league/preflight.py` — 165 lines
   - `common/transport/audit.py` — 161 lines
2. `scripts/check_planning_graph.py` reports **6** issues (one more than thief_repo):
   - `T030` `read_set`/`write_set` self-overlap on `common/transport/series.py`.
   - `T009`/`T030` write-set overlap on `common/transport/series.py` — blocks `T035`/`T039`.
   - `T016`/`T032` write-set overlap on the reporting schema/config/test paths.
   - `T007-extend-wire-brain-swap`'s `read_set` overlaps its own `write_set` on
     `src/police_peer/wire/__init__.py` (harmless but should be trimmed).
   - `T007-extend-kpi-harness` and `T007-extend-wire-brain-swap` both have a **dangling
     `depends_on: PS-01`** — `PS-01` is not a registered task ID in this repository's task
     graph (it appears to be an ID from the `police-strategy` branch's own internal
     `docs/TODO_police_strategy.md` numbering, never registered as a `T###` task here).
     This is a real governance defect: these two write-set-extension records reference an
     ID the planning graph cannot resolve.

## Expected outcome (this task)

- `config/repo_quality.toml`'s `source_dirs = ["src", "common"]`.
- `T009`/`T030` and `T016`/`T032` overlaps reconciled (narrowed write-sets or sequencing).
- `T007-extend-kpi-harness.md` and `T007-extend-wire-brain-swap.md` either get `PS-01`
  replaced with the correct registered `T###` dependency, or (if `PS-01` genuinely has no
  `T###` equivalent) `depends_on` is cleared and the informal dependency is described in
  prose instead — do not leave a dangling reference.
- `scripts/check_planning_graph.py` added to the quality-gate workflow once clean.
- README/TODO staleness corrected, including reconciling that PR #34's head has moved to
  `c335818` (Phase D work) since this pack was pinned at `5f7c3bf`.

## Explicitly NOT in this task's scope

- Do **not** compress code or weaken the 150-line rule. The 6 files above are a starting
  inventory for later behavior-preserving splits, executed separately.

## Acceptance criteria

- [ ] `config/repo_quality.toml` has `source_dirs = ["src", "common"]`.
- [ ] `scripts/check_planning_graph.py` reports 0 issues (including the `PS-01` dangling dependency).
- [ ] The 6 over-limit files are each behavior-preservingly split under 150 logical lines (separate execution pass).
- [ ] `scripts/check_planning_graph.py` runs as part of `scripts/run_quality_gates.py` or CI.
- [ ] `docs/TODO.md`/`README.md` reflect actual `police-strategy` branch state.

## Verification

- `uv run python scripts/check_planning_graph.py`
- `uv run python scripts/check_line_cap.py src common`
- `uv run python scripts/run_quality_gates.py`

## Handoff contract

Report files changed, tests executed, exact results, decisions, deviations, blockers.

## Result and evidence
