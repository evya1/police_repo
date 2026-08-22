# Wave A2 Handoff

## Scope
T003 / T004 / T028 / T029 / T009 / T010

## Base
- Police base SHA: `df003a3159be58cc44e0ae655e657db4056e3910`
- Thief base SHA: `e250f91d6651cc23a9bfd7f5302754057fce26c6`

## Current candidate
- Branch: `task/T003-runtime-boundary-final`
- Current Police candidate SHA: `8852f2f9f6f4070aca8c6f6ee5753273159d9b9f`
- Current Thief candidate SHA: `5abd5f900c3b8421c4c388f87c1ba6172757638a`
- PR URLs:
  - Police PR #32: https://github.com/evya1/police_repo/pull/32
  - Thief PR #33: https://github.com/evya1/thief_repo/pull/33

## Implemented
- T003: Public package and CLI/SDK entrypoints (`src/police_peer` / `src/thief_peer` with `__init__.py`, `__main__.py`, `sdk.py`, `cli.py`, `runner.py`, `strategy.py`).
- T004 + T028: Equal-threshold operational contract (`max_moves == survival_threshold == 35`) with divergence refusal; sanitized `config/game.example.json` and `config/game.toml.example`.
- T029: Deterministic Stage-1 capture/survival test coverage and domain verification.
- T009 + T010: Independent one-peer FastMCP CLI and runner (`python -m police_peer` and `python -m thief_peer`) starting local server and connecting to peer endpoint using a single local `PeerFacade`.

## Validation completed
- Full pytest test suites passing (100% passing across unit, integration, and contract suites).
- Ruff check passing with zero errors across all files.
- Repository quality gates passing.
- GitHub CI status: `verify` workflow PASSED for both PR heads.
- Thread-based two-peer HTTP loopback smoke test (`tests/integration/test_two_process_smoke.py`) passed.

## Independent review
- Reviewer Model: `deepseek/deepseek-v4-pro-0813`
- Verdict on initial candidate (`e38f3ed` / `8dd7d02`): `CHANGES_REQUESTED`
- Findings:
  - BLOCKER 1: `[tool.uv] package = false` skipped entrypoints in default `uv` workflow.
  - BLOCKER 2: `common` package omitted from build config.
  - HIGH: `StandInEngine.start_subgame` hardcoded `(0,0)` and `(3,3)` instead of deriving from negotiated `terms`.
  - MEDIUM: `--mode` parameter accepted by CLI but unhandled in runner context.
  - LOW: `create_peer(channel=None)` loopback behavior.
  - NIT: `test_two_process_smoke.py` runs inside threads rather than two separate OS processes.
- Saved Review Verdict Artifact: `/root/supervisor_runs/review_a2/verdict.txt`

## Remaining required repair & verification
- Fixer commit `8852f2f` (Police) and `5abd5f9` (Thief) implemented packaging build-system configuration, dynamic start position extraction from terms, and mode handling.
- Deterministic verification required:
  1. Prove CLI execution via `uv run python -m police_peer` and `uv run python -m thief_peer`.
  2. Prove true separate-OS-process execution over HTTP with two distinct PIDs.
  3. Re-review by independent DeepSeek V4 Pro reviewer.

## Acceptance gate before merge
1. Both PRs (#32 and #33) must pass independent DeepSeek V4 Pro re-review with verdict APPROVE.
2. Verified zero BLOCKER and zero HIGH findings.
3. Paired fast-forward merge to Police and Thief masters.

## Next downstream barrier
- Completion of A2 unblocks:
  - Wave B2: T014 Live GUI (consuming CT-05 event projection).
  - Wave A3: T013 Step 0 Evidence & T011 Reliability.

## Resume instructions
1. Read `/root/supervisor_runs/CONTROLLER_STATE.md` and `/root/supervisor_runs/RESUME_HANDOFF.md`.
2. Inspect PR #32 and #33 current heads (`8852f2f` and `5abd5f9`).
3. Run two-OS-process smoke test and verify packaging entrypoints.
4. Dispatch fresh DeepSeek V4 Pro re-review session.
5. If APPROVE, merge PR #32 then PR #33 to masters, then launch Wave A3 and Wave B2.
