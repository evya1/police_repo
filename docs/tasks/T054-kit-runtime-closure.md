---
id: T054
status: in_review
priority: P2
task_type: component
component: C04
optional: true
implements:
  - NET-001
  - NET-002
  - SEC-005
  - SEC-006
  - ARCH-004
context_files:
  - docs/PRD.md
  - docs/PLAN.md
  - docs/interop/LEAGUE_COMPATIBILITY.md
  - docs/decisions/ADR-011-league-kit-interoperability-boundary.md
read_set:
  - common/transport/audit.py
  - common/transport/replay.py
  - common/transport/replay_types.py
  - common/transport/turnfeed.py
depends_on:
  - T027
  - T030
  - T035
  - T039
  - T040
  - T044
  - T052
gates: []
parallel_safe: false
claimed_by:
claim_expires_at:
write_set:
  - common/transport/audit_wire.py
  - common/transport/opponent_pin.py
  - common/transport/subgame.py
  - common/transport/series.py
  - common/transport/run_series.py
  - common/transport/replay_evidence.py
  - src/police_peer/sdk.py
  - src/police_peer/wire/startup.py
  - src/police_peer/wire/sealed_payload.py
  - src/police_peer/wire/session.py
  - src/police_peer/wire/brain.py
  - src/police_peer/wire/stand_in.py
  - src/police_peer/wire/negotiate_per_subgame.py
  - config/repo_quality.toml
  - tests/fixtures/league_kit/
  - tests/contract/test_league_kit_vectors.py
  - tests/integration/kit_audit_harness.py
  - tests/integration/test_league_kit_production_audit.py
  - tests/integration/test_sealed_position.py
  - tests/unit/wire/test_opponent_pin.py
  - tests/unit/wire/test_negotiate_per_subgame.py
risk: high
---

# T054 — Production `reference-v3` runtime closure

## Why this task exists

T052 was marked `done` while every conversion it built was dead code. The helpers passed
their unit tests; the runtime never called them. A unit helper that is green while the
production path bypasses it is not interoperability — it is the appearance of it.

T052 is reclassified `in_review`; its history is not rewritten. This task owns the closure.

## Defects closed (each with a failing-before observation)

| # | Defect | Failing-before observation, recorded before the fix |
|---|---|---|
| 1 | Sealed payload omitted post-move `position` | 210 sealed move records across six sub-games carried no `position`; the kit's `examples/verify_pairing_physics.py` dereferences it and cannot walk the game without it |
| 2 | Kit audit never wired to production | `create_peer()` had no wire-profile seam at all (`TypeError: unexpected keyword argument 'wire_profile'`) |
| 3 | Kit `sender` semantics unpinned | same — no production path could produce a kit audit to assert against |
| 4 | First-opponent pin lost between sub-game 1 and 2 | with a peer that renamed itself `teamC-impostor` from sub-game 2 onward, **A never refused**: it adopted the impostor as its pin and died later on an unrelated `TimeoutError` |
| 5 | Contract suite skipped on a developer path | the Police suite reported `1254 passed, 6 skipped` and then `0 skipped` with no code change between the runs — purely because a checkout appeared at a hard-coded absolute path |

## What was implemented

### One audit-wire port, two adapters

`common/transport/audit_wire.py` introduces the narrow port and both implementations:

- `IdentityAuditWire` — the default internal lane, byte-for-byte what T046/T047 publish.
- `KitAuditWire` — `reference-v3`: top level exactly `sender` / `records` / `result_claim`,
  each record nested around the **exact** payload that was already committed.

Neither adapter hashes anything. Outbound wraps an already-sealed payload, so there is
still exactly one commitment authority. Inbound normalizes *before* the existing verifier,
which is unchanged — same decoder, same verdict taxonomy, same coverage discipline.

`sender` is the producing **role** (`police` / `thief`), never the group ID; `result_claim`
stays the settled outcome **string**. Missing or wrongly typed required fields are refused
(`SPAR-A01`) before any state mutates; unknown extra top-level fields are tolerated, because
refusing a peer for carrying more than we know about is a self-inflicted interop failure.

`create_peer(..., wire_profile=...)` resolves the adapter once, at composition. An unknown
profile fails fast at startup rather than silently falling back to the internal lane.

### One series-owned opponent pin

`common/transport/opponent_pin.py` holds the pin the whole series is bound to.
`create_peer` builds one and hands the **same object** to both `PeerFacade` and
`negotiated_subgame_driver`, so the opponent verified in sub-game 1's greeting is already
bound when sub-game 2 negotiates. `bind()` refuses a changed group before state mutates;
re-binding the same group is idempotent, because a re-greeting by the same peer is ordinary
and only a genuine *change* is a fault.

### Post-move `position` at one construction boundary

`src/police_peer/wire/sealed_payload.py` now owns both `build_result` and
`build_terminal_final`. `position` is derived once, from the engine's own state after the
action is applied and before the record is committed. It is **never** appended to the
envelope after hashing, and `PUBLIC_TURN_KEYS` does not project it, so it reaches neither
the opponent's turn message nor an LLM prompt.

Both wire adapters compose these two functions instead of each keeping a copy: a drift
between the two engines would surface only as an opponent's audit failure.

### Portable pinned fixtures

`tests/fixtures/league_kit/ad65576/` carries the four vector files the contract suite
consumes, the kit's verbatim MIT `LICENSE`, and a `PROVENANCE.md` recording upstream URL,
pinned commit and per-file SHA-256. The contract module can no longer skip; a guard test
asserts the fixtures are present. No `/home/user/...` path remains anywhere in `common/`,
`src/`, `tests/` or `scripts/`. Live K0/K2 checks take an explicit `--kit-root`.

## Line-cap effect (ratchet tightened, not widened)

The splits this task required moved two files off the baseline entirely:

| File | Before | After |
|---|---:|---:|
| `common/transport/series.py` | 183 (baselined) | 149 |
| `src/police_peer/wire/session.py` | 173 (baselined) | 125 |

Baselined files: **7 → 5**. No file was compressed to pass; each was split along a real
seam (`run_series.py`, `sealed_payload.py`, `startup.py`).

## Verification

```sh
uv run pytest tests/integration/test_sealed_position.py \
  tests/integration/test_league_kit_production_audit.py \
  tests/unit/wire/test_opponent_pin.py \
  tests/unit/wire/test_negotiate_per_subgame.py \
  tests/contract/test_league_kit_vectors.py -q
uv run ruff check .
uv run pytest
uv run python scripts/run_quality_gates.py
uv run python scripts/check_line_cap.py
```

## Completion rule

T054 is **not** `done` on green unit helpers. It is done when the failing-before
production-path observations above pass after the fix — and even then, project status stays
below `kit_interop` until T053 (artifact projection) and T022 (K0-K4) both pass.
