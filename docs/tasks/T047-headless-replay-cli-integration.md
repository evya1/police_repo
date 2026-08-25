---
id: T047
status: done
priority: P0
task_type: component
component: C05
optional: false
implements:
  - OBS-006
  - OBS-007
  - QR-006
context_files:
  - docs/components/C05-observability-replay/PRD.md
  - docs/components/C05-observability-replay/PLAN.md
  - docs/PRD_replay_port.md
  - docs/PLAN_replay_port.md
read_set: []
depends_on:
  - T033
  - T038
  - T046
gates: []
parallel_safe: true
claimed_by:
claim_expires_at:
write_set:
  - src/police_peer/replay_service.py
  - src/police_peer/sdk.py
  - scripts/replay.py
  - scripts/smoke_replay_integration.py
  - scripts/check_replay_parity.py
  - tests/unit/test_replay_service.py
  - tests/integration/test_replay_cli.py
  - tests/integration/test_cross_peer_replay.py
  - tests/integration/test_replay_trust_levels.py
  - tests/fixtures/replay/sibling_v1/
  - docs/evidence/replay/
risk: medium
---

# T047 — Replay application service, SDK, CLI, and cross-peer evidence

## Expected outcome

One application use case loads and verifies a published bundle. The SDK is the only programmatic
entry point; the CLI is argument parsing, printing, and exit-code mapping only. A bundle produced by
this repository verifies in the sibling repository and vice versa.

## Requirements implemented

- `OBS-006`
- `OBS-007`
- `QR-006`

## Relevant context

Implements RP-02, RP-03, RP-09, RP-11, and RP-12 of `docs/PRD_replay_port.md`. REVIEW_FINDINGS F-05: the previous
`_terms_beside()` chose the lexicographically first `config_*.json` rather than the config belonging
to the log. F-06: `cross_check_uid()` ignored malformed JSON and documents without a UID, so an empty
or incomplete directory could pass.

T015 (GUI replay view) consumes `ReplayReport` from this service and performs no hashing of its own.

T047 depends on **T038**, which owns `src/police_peer/sdk.py`. The dependency is what serializes
that shared path; the two tasks must never run in the same wave.

## Constraints

- Edit only the declared write set.
- The CLI may import only `argparse`, `json`, `pathlib`, `sys`, and the SDK entrypoint. It contains
  no hashes, no physics, and no artifact pairing.
- No runtime import of the sibling repository; cross-peer verification copies bundle bytes only.
- Every code and test file stays below 150 logical lines.
- Evidence transcripts are sanitized; no secrets, private identifiers, or credentials.

## Acceptance criteria

- [x] The service loads exactly one UID directory, requires and validates the manifest, checks exact
      membership and per-file digests, and rejects unexpected members inside the directory.
- [x] Every log is paired with its exact config by matching `game_id`, `sub_game_index`, and
      `game_uid`. Zero matches and multiple matches are both failures, never success.
- [x] The service calls the pure `verify_replay` and aggregates a `BundleReplayReport` with stable
      JSON and human projections that print the per-layer coverage and the external-authenticity
      status explicitly.
- [x] Manifest validation also checks cross-document expected record counts and final steps (RP-12).
- [x] Exit codes: 0 verified, 4 illegal, 5 invalid or incomplete, 6 tampered, 2 path/usage error.
- [x] `src/police_peer/sdk.py` exports `verify_replay_bundle(path) -> BundleReplayReport` as the only
      application entrypoint.
- [x] Sanitized honest, tampered, and unanchored-recomputed transcripts are generated under
      `docs/evidence/replay/`. The recomputed bundle may be internally consistent, yet it is reported
      with `external_authenticity=false` and is never described as authentic.
- [x] `scripts/smoke_replay_integration.py` and `scripts/check_replay_parity.py` implement the
      contracts in the shared test strategy: the smoke script drives the public SDK composition path
      end to end, and the parity script hashes shared bytes and invokes each repository's CLI as a
      **subprocess in that repository's own working directory**.
- [x] A bundle produced by this repository verifies with the sibling's replay CLI and vice versa,
      using frozen fixtures under `tests/fixtures/replay/sibling_v1/` or separate subprocess CLIs.
      The sibling package is never imported at runtime. `diff -rq` shows `common/` byte-identical
      across both repositories.

## Verification

- `uv run pytest tests/unit/test_replay_service.py tests/integration/test_replay_cli.py tests/integration/test_cross_peer_replay.py tests/integration/test_replay_trust_levels.py`
- `uv run python scripts/replay.py <honest-dir>`
- `uv run python scripts/smoke_replay_integration.py --help`
- `uv run python scripts/check_replay_parity.py --sibling-root ../thief_repo`
- `diff -rq ../thief_repo/common common`
- `uv run ruff check .`
- `uv run pytest`
- `uv run python scripts/run_quality_gates.py`

## Result and evidence

Validated on `production-fixes`. The replay service, SDK entrypoint, CLI exit mapping, sanitized
trust-level evidence, smoke integration, and reciprocal Police/Thief verification are implemented
and covered by the declared tests. The combined completion audit passed 209 tests with no failures
on 2026-08-24.
