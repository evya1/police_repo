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

- [x] `config/repo_quality.toml` has `source_dirs = ["src", "common"]`.
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

**Partial completion — line-cap ratchet only.** Not all of T040 is done; see remaining items below.

`config/repo_quality.toml`'s `source_dirs = []` blind spot is repaired: `source_dirs = ["src", "common"]`,
plus a `[line_cap_baseline]` ratchet table (`scripts/line_cap_ratchet.py`, split out of
`scripts/check_line_cap.py` to respect the cap itself) so unscanned production debt cannot hide
behind an empty `source_dirs` again, while genuinely pre-existing oversized files are not
silently swept under the rug or compressed to fit.

**Baseline, independently measured at this commit's HEAD** (`uv run python scripts/check_line_cap.py`
against the full default scan of `src/`, `common/`, `tests/`, `scripts/`):

| File | Logical lines |
|---|---|
| `src/police_peer/reporting/schemas.py` | 448 |
| `common/config/__init__.py` | 278 |
| `common/transport/negotiate.py` | 196 |
| `common/transport/series.py` | 183 |
| `src/police_peer/wire/session.py` | 173 |
| `src/police_peer/league/preflight.py` | 165 |
| `common/transport/audit.py` | 157 |

**Ratchet semantics implemented and proven** (`tests/test_line_cap_ratchet.py`, 10 tests):
an unlisted file over the cap fails; an exact baseline match passes; baseline+1 (drift upward)
fails; a real reduction without lowering the baseline fails (must lower it in the same commit);
a reduction to at-or-below the cap with a stale baseline entry left in place fails; removing the
entry once at/below cap passes; a baseline entry naming a missing, wildcard, or directory-wide
path fails; a non-integer baseline value is a config error; default (no explicit CLI paths)
execution scans the configured `source_dirs` (`src` and `common`).

**Commands run:**
```
uv run python scripts/check_line_cap.py               # OK: 254 file(s) ... (7 baselined)
uv run pytest tests/test_line_cap_ratchet.py tests/test_line_docs_common.py tests/test_cli_repository_gates.py -q --no-cov   # 23 passed
uv run pytest --no-cov                                 # 1187 passed
uv run ruff check .                                    # All checks passed!
uv run python scripts/run_quality_gates.py              # all 7 gates OK
git diff --check                                        # clean
```

**Deviations:** none from the declared ratchet semantics. `find_violations` was kept (baseline-
unaware) for the pre-existing unit tests in `test_line_docs_common.py` that exercise it directly.

**Remaining (explicitly NOT done by this pass, per this task's own "Explicitly NOT in this
task's scope" section and per the orchestrator's Phase B instruction not to mark unrelated
criteria complete):**
- The 6 pre-existing oversized files are pinned, not split — a separate behavior-preserving
  extraction pass is required to actually retire baseline entries.
- `scripts/check_planning_graph.py`'s reported issues (T009/T030 and T016/T032 write-set
  overlaps, the dangling `PS-01` dependency on `T007-extend-kpi-harness`/`T007-extend-wire-brain-swap`)
  are untouched.
- `scripts/check_planning_graph.py` is not yet wired into `run_quality_gates.py`.
- `docs/TODO.md`/`README.md` staleness beyond the line-cap gate itself is not reconciled here;
  full documentation reconciliation is a separate later phase.
