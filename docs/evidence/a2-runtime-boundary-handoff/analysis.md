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

## Accepted result

Fixer commits `8852f2f` (Police) and `5abd5f9` (Thief) completed packaging configuration,
term-derived start positions, and mode handling. The CLI entrypoints, separate-process HTTP play,
quality gates, and downstream GUI/evidence integrations are verified on `production-fixes`.
