---
artifact: stage-todo
id: TODO-MCP-INFRA
status: active
version: 0.4
derived_from: PLAN-MCP-INFRA@0.1 · PRD_mcp_infrastructure (approved 2026-08-17)
applies_to: police_repo + thief_repo
owner: orchestrator
updated 2026-08-17 (ST-03 + ST-04 + ST-05 done)
---

# TODO — MCP Infrastructure (Stage 2)

Task ledger for building the MCP infrastructure from `PRD_mcp_infrastructure.md` + `PLAN_mcp_infrastructure.md`. Order is **top-down** (PLAN §1.1): the full series runs end-to-end over loopback in phase A, then stubs are replaced layer by layer, and the last swap is loopback → real FastMCP. **Big-bang integration is not allowed** — no stage is done while the spine test is red, and no stage builds shared modules without wiring them into the series in the same stage.

## How this ledger works

- **Status values:** `not started` · `in progress` · `blocked` (names the dependency/gate) · `done` (orchestrator-verified evidence only).
- **Ready rule:** a stage task is ready when every `depends on` task is `done` and no gate blocks start. `G-LIVE` blocks ST-15's live criteria only — the local suite never waits on it.
- **Responsibility:** `ORC` = orchestrator; `IA` = implementation agent (claims the mapped repo task per `AGENTS.md`, edits only its write set, hands off with evidence: files changed, tests executed, exact results, decisions, deviations, blockers, newly discovered work).
- **Repo mapping:** the repo task files (`police_repo/docs/tasks/`) remain the claim units. Each stage task names the repo task(s) it executes. The orchestrator reconciles the repo `TODO.md` after every stage.
- **Progress:** the IA updates `status` (and claim fields in the repo task file) while working; the ORC verifies evidence before `done` and marks the stage gate passed.
- **Spine invariant:** `tests/integration/test_series_loopback.py` green after **every** stage (PLAN §12 invariant 1).

## Stage task index

| ID | Task | Phase | Pri | Status | Owner | Depends on | Maps to (repo / PRD) | Gate |
|---|---|---|---|---|---|---|---|---|
| ST-01 | Prerequisites (write-set retarget, num_games, fastmcp dep, coverage config) | A | P0 | done | ORC | — | O-1/ADR-005 · O-2 · T002 | G-S1 |
| ST-02 | Transport seam + loopback transport + module skeletons | A | P0 | done | IA | ST-01 | T009 · FR-6/7/8 | G-S1 |
| ST-03 | End-to-end skeleton series over loopback (top of the tree) | A | P0 | done | IA | ST-02 | T009 · FR-3/18/19/41 | G-S1 |
| ST-04 | Byte-level primitives + golden vectors (M1) | B | P0 | done | IA | ST-03 | T008 · FR-12/15 | G-S2 |
| ST-05 | Terms layer + private config wiring | C | P0 | not started | IA | ST-03 (∥ ST-04) | T009 · FR-11/40 | G-S3 |
| ST-06 | Handshake: negotiation, refusals, pairing, locks, uid | C | P0 | not started | IA | ST-04, ST-05 | T009 · FR-10…16, 18, 20 | G-S3 |
| ST-07 | Turn frames: shapes + all-or-nothing validation | C | P0 | not started | IA | ST-03 (∥ ST-04…06) | T009 · FR-21…27 | G-S4 |
| ST-08 | At-least-once inbox + deterministic fault injection (M3) | D | P1 | not started | IA | ST-07 | T012 · FR-32/33/34 | G-S4 |
| ST-09 | Mutual audit + TAMPERED sanction (M4-loopback) | E | P0 | not started | IA | ST-08 | T008 · FR-28/29/42 | G-S5 |
| ST-10 | FastMCP server (M2) | F | P0 | not started | IA | ST-03 (∥ phases B–E) | T009 · FR-4/6/8/9/19/37 | G-S6 |
| ST-11 | FastMCP client + two-process localhost smoke (M2) | F | P0 | not started | IA | ST-06…10 | T009 · FR-3/7/30 | G-S6 |
| ST-12 | Session faults + recovery suite (M4) | G | P1 | not started | IA | ST-11 | T012/T022 · FR-31 | G-S7 |
| ST-13 | Tunnel readiness discipline (M5-local) | H | P1 | not started | IA | ST-11 (∥ ST-12) | T009/T022 · FR-35/36 | G-S8 |
| ST-14 | Guards + cross-repo sync + Stage-2 system proof | H | P0 | not started | IA | ST-12, ST-13 | T022 · FR-1/2/38/39, SC-1…7 | G-S8 |
| ST-15 | Live interop + public endpoint (M5-live) | H | P1 | not started | IA + ORC | ST-14, G-LIVE | T022 · FR-35, SC-5 | G-S9 |

Phase → milestone map: A = spine (new, pre-M1) · B = M1 · C = M2a/M2b · D = M3 · E = M4 (loopback proof) · F = M2 (`local_mcp_smoke` + `reference_v3_contract`) · G = M4 (system) · H = M5.

---

## Phase A — Prerequisites and the top of the tree

### ST-01 — Prerequisites (owner: ORC)

Scope (documentation/config only, no protocol code):

- **F-1** Retarget the C03 PLAN (`docs/components/C03-peer-protocol-integrity/PLAN.md`) and the write-sets of T008 (`integrity/`), T009 (`transport/`), T012 (`transport/inbox.py`) from `src/<role>_peer/` to `common/transport/`; add `docs/decisions/ADR-005-shared-protocol-layer-placement.md` to T009's `context_files`. Both repos (O-1, ADR-005 pending item).
- **F-2** Fix `num_games: 1 → 6` in `config/game.json` in **both** repos (O-2; the kit's fixed binding and T028 say 6).
- **F-3** Add `fastmcp>=2.0,<3.0` to `dependencies` + regenerate the lock (repo task T002; approved lock required before ST-10).
- **F-4** Extend pytest coverage `source` in `pyproject.toml` to include `common` (stage code must count toward the 85% gate).

**Definition of done:**
- [ ] `uv run python scripts/check_planning_graph.py` passes in both repos (29 tasks, graph unchanged and acyclic).
- [ ] T008/T009/T012 task files name `common/transport/` paths; C03 PLAN names the location.
- [ ] `config/game.json` has `num_games: 6` in both repos; `uv run pytest tests/unit/domain` green.
- [ ] `uv sync --locked --all-groups` succeeds; `import fastmcp` works in the venv.
- [ ] Coverage reports `common` in its source list.

### ST-02 — Transport seam, loopback transport, module skeletons (owner: IA)

Build (PLAN §5.10, §5.11):

- `common/transport/__init__.py` (exports only), `common/transport/transport.py` — the `PeerChannel` protocol exactly as specified (4 `send_*` + 4 `poll_*` + `close`); the `send_audit(payload)` vs `send_agreement(message)` asymmetry is in the signature.
- `common/transport/loopback.py` — `Inboxes` (4 deques + `drain`), `LoopbackPeer` (4 tools: validate shape, enqueue, return `{"ok": True}` — never block, FR-8), `LoopbackTransport` (implements `PeerChannel`), `pair()`.
- Skeleton files for the remaining shared modules (`canonical, integrity, ids, terms, locks, negotiate, refusals, messages, inbox, audit, series, faults, mcp_server, mcp_client, probes, readiness, guards`) with module docstrings citing their FR ids and honest `STUB` bodies (`raise NotImplementedError`).
- `tests/unit/transport/test_loopback.py` — round-trip all four tools over loopback; assert the four tool names; assert the `submit_audit(payload)` vs `negotiate(message)` argument asymmetry at the loopback surface (FR-6/FR-7, TC-01/TC-02 shape).

**Definition of done:**
- [ ] `uv run pytest tests/unit/transport/test_loopback.py` green; ruff clean.
- [ ] `import common.transport` succeeds with **no** `fastmcp` import anywhere in the package (source-scan: zero `fastmcp` imports — the boundary is provable from ST-02).
- [ ] Every skeleton module imports cleanly and its stub bodies raise `NotImplementedError` (honest — the spine test of ST-03 fails on them until each layer lands).
- [ ] `scripts/check_common_sync.py` placeholder wired (script lands in ST-14; for now a `diff -rq` one-liner in the handoff shows 0 differing files vs the sibling repo).

### ST-03 — End-to-end skeleton series over loopback (owner: IA) — **the top of the tree** ✅ DONE

Build (PLAN §5.13, §5.14; SD-01/SD-02/SD-03):

- `common/transport/series.py` — **real**: `Budgets`, `PeerConfig`, the `TurnEngine` protocol, `PeerFacade` (both-dial rule, per-sub-game negotiation with the derived role (`role_for` — odd sub-games: natural role, even: opposite), full-turn alternation with the thief moving first (FR-18; wire `step` = the sender's own move number, 1..`max_steps` per side), inbox drain + deadline check **every lap**, terminal (capture/survival/timeout) → audit exchange → per-sub-game reset, 6-sub-game loop, ledger settled by the shared `settled_outcome` (a failed audit ⇒ `TAMPER_FORFEIT`, both zeroed; a zeroed outcome owes no audit), turn-order diagnostic that **names** the disagreement — FR-18), `SeriesResult`, `run_series` (loopback: two threads in one process).
- Stubs replaced by **marked STUB implementations** (each drop-in behind its shared function, PLAN §12): `canonical.py` (`sha256(str(sorted-repr))` placeholder), `integrity.py`/`ids.py` (placeholder commit/uid built on the stub canonical), `negotiate.py` (accept-all greeting), `messages.py` (passthrough turn dict), `inbox.py` (FIFO, no dedup/window), `audit.py` (always-pass verdict).
- Role glue in **both** repos: `src/{police,thief}_peer/wire/{__init__,engine,policy_stub,config,entry}.py` — `StandInEngine` over the **existing stage-1 domain** (one fresh `common.domain.rules.GameEngine` per sub-game — `apply_own_move`, `observe_barrier`, `answer_capture_claim`, `self_captured`, `survived`, `state_string`) + the role `scent` model for the transmitted grid, sealing the draft role-local record payload (PLAN §5.14, labeled non-official; `state` = the SPEC-pinned `state_string`, own position only); `StubPolicy` (seeded deterministic; zero-token template hints, `intent` per FR-42); private config loader (incl. `natural_role`, default = pairing-playbook convention, labeled a default); CLI with `--loopback` mode (two in-process peers on threads) + `--role/--peer/--host/--port` stubs for the later real mode.
- `tests/integration/test_series_loopback.py` — **the spine**: full series (handshake → six sub-games → mutual audits) settles over loopback; ledger has 6 rows (roles alternate across sub-games per `role_for`); the thief (by per-sub-game role) makes the first move and each frame's `step` is the sender's own move number (FR-18); both sides pushed turns (neither only listened, FR-3); no step-0 message and no `hello` tool exist on the surface (FR-19); audit verdicts `passed=True` (stub); deterministic seed ⇒ byte-identical ledger across two runs (NFR-1, first run).
- `tests/unit/transport/test_series_turnorder.py` — TC-28: two facades that each expect the other to open ⇒ the diagnostic names the turn-order disagreement, not a bare timeout.
- `tests/unit/transport/test_policy_stub.py` — TC-27: hint-provider failure path ⇒ the zero-token template produces the hint and the legal action proceeds (FR-41); hint text carries no numeric position (FR-27 first check).

**Definition of done:**
- [x] Spine test green: full six-sub-game series settles over loopback in CI with **no fastmcp, no sockets, no sleeping** (NFR-2).
- [x] TC-27, TC-28 green; every stub body carries a `STUB` marker and its FR citation.
- [x] `uv run pytest` + `uv run ruff check .` green in the dev repo; role glue mirrored byte-identical in logic (role constants differ) to the sibling repo; `diff -rq` on `common/transport` = 0.
- [x] Handoff evidence: ledger printout of a run + seed.

**Implementation notes:**
- `series.py` implemented with real `PeerFacade` and `run_series` using two threads in one process for loopback
- Greeting exchange converts `Greeting` dataclass to/from dict for transport compatibility
- Turn alternation: thief moves first (FR-18), each side's `step` is their own move number
- Stub audit always passes; `settled_outcome()` handles settlement
- Spine test (`tests/integration/test_series_loopback.py`) verifies 6-row ledger, role alternation, deterministic seed
- Fixed missing `common/__init__.py` and `common/domain/*` files in thief_repo
- Fixed missing `tests/conftest.py` in thief_repo
- All stub modules carry `STUB` marker and FR citations

---

## Phase B — M1: byte-level primitives

### ST-04 — Canonicalization, commit, uid + golden vectors (owner: IA → repo task T008) ✅ DONE

Build (PLAN §5.1–5.3): replaced the STUBs in `canonical.py` (exact kit recipe: `sort_keys=True, ensure_ascii=False, separators=(",",":")`, UTF-8), `integrity.py` (`new_nonce`, `commit` — nonce pipe-appended, `terms_signature`), `ids.py` (`game_id` sorted pair, `game_uid` first 16 digest bytes → UUID). Vendor the kit's golden fixtures into `tests/contract/vectors/` (`canonical_json.json`, `commit_reveal.json`, `terms_signature.json`, `game_uid.json`, `delivery_contract.json`, `locked_model.json`, `pairing_declaration.json`, `turn_message.json`) with provenance recorded (upstream SHA per EVID-003; non-authoritative, PRD C1). `tests/contract/test_golden_vectors.py` reproduces every vendored vector byte-for-byte (TC-25, T008 `{#early_byte_vectors}` — run here, not deferred to T022).

**Definition of done:**
- [x] TC-25 green: 100% of vendored vectors reproduced (terms signature, commit, uid derivation, canonical JSON incl. Unicode + float repr cases).
- [x] Spine still green with real hashes (drop-in replacement verified).
- [x] Nonce secrecy test: a grep of the series' logs/frames shows no nonce before the audit (SEC-004, NFR-6).
- [x] `uv run pytest tests/unit/transport tests/contract/test_golden_vectors.py tests/integration/test_series_loopback.py` green; handoff includes the vector-run output.

**Implementation notes:**
- Removed STUB comments from `canonical.py`, `integrity.py`, `ids.py` (both repos, byte-identical).
- `canonical_bytes`: RFC 8785 canonical JSON — sorted keys, compact separators, `ensure_ascii=False`, UTF-8.
- `commit`: SHA-256 over `canonical_bytes(payload) + nonce.encode()` (pipe-appended).
- `game_id`: sorted-pair string, order-independent.
- `game_uid`: first 16 bytes of SHA-256(game_id|terms_hash) → UUID hex.
- `terms_signature`: SHA-256 over canonical `{"shared": ..., "private": ...}`.
- Vendored 8 golden fixtures into `tests/contract/vectors/` with provenance recorded.
- Added `tests/unit/transport/test_canonical.py` (18 tests), `test_integrity.py` (8 tests), `test_ids.py` (16 tests).
- Added `tests/contract/test_golden_vectors.py` (8 test classes, 23 test methods) — TC-25.
- Both repos: 85 tests green, ruff clean, common/ byte-identical.

---

## Phase C — Handshake and turn frames

### ST-05 — Terms layer + private config wiring (owner: IA → repo task T009) ✅ DONE [L139-148]

Build (PLAN §5.4, §11): `terms.py` — `TERMS_KEYS` (exactly 14), `project_terms(shared, private)` implementing the PRD §9.2 projection table (incl. `min_center_intensity` from private TOML / fixed 0.5 labeled non-official; `num_games` must be 6), `terms_diff`. Role `wire/config.py` real: `PrivateConfig` from `game.toml` + `PeerConfig` assembly from the C01-validated `game.json` snapshot (JSON overlays TOML on conflict, CFG-003). Unit tests for the projection (all 14 keys present, closed, sourced per the table) and for the overlay rule.

**Definition of done:**
- [x] Projection unit tests green (29 tests: 3 TERMS_KEYS, 17 project_terms, 6 terms_diff, 3 empty/defaults) — all 14 keys present, closed, sourced per the §9.2 table; `terms_diff` detects wrong/extra/missing keys.
- [x] Spine green (`test_series_loopback.py` passes — greeting carries projected terms; accept-all verification confirmed, ST-06 handles refusal).
- [x] `setting` value check: `project_terms` sources `"New York"` from `config/game.json` (`world.map_area`); `"Haifa"` is the stock kit peer default — flagged for ST-11 sparring decision (PRD §9.2).

**Implementation notes:**
- `TERMS_KEYS` updated from old 14 keys to PRD §9.2 table keys (board_size, smell_grid_size, decay_per_step, emit_intensity, min_center_intensity, max_steps, barriers_max, setting, hint_max_words, axis_origin_corner, axis_start_index, thief_start, cop_start, num_games).
- `project_terms` implements the full projection table; `num_games` fixed at 6 (O-2 discrepancy override); `min_center_intensity` sourced from private TOML with default 0.5 (FR-11, non-official).
- `wire/config.py` created in both repos: `PrivateConfig` (dataclass), `load_private`, `build_peer_config` (CFG-003: JSON wins), `assemble_peer_config`, `verify_terms_closed`.
- Tests: `tests/unit/transport/test_terms.py` (29 tests) + `tests/unit/wire/test_config.py` (18 tests) in both repos.
- Ruff: clean. Common dirs byte-identical across repos.

### ST-06 — Negotiation, refusals, pairing, locks, uid (owner: IA → repo task T009)

Build (PLAN §5.5, §5.6): `locks.py` (families, pinned doc + hash, `lock_decision`), `negotiate.py` (`Greeting` with the FR-20 omission convention, `our_greeting`, `verify_greeting` with the **fixed FR-13 order** — terms present → 14 keys → value-equality → signature re-verify with our own serializer (both canonical strings on failure) → locks → pairing → declared uid), `refusals.py` (SPAR-N00…N10 codes + actionable diagnostics; the pairing/uid decision tables — omission never refuses, FR-14/FR-16), refusal sent via `receive_control` and no game state created on refusal (US-MCP-006).

**Definition of done:**
- [ ] TC-03 (valid 14-key terms + signature accepted; single value mismatch refused with the key named), TC-04 (serializer drift, e.g. `ensure_ascii=True` ⇒ signature refusal with both canonical strings printed), TC-05 (two `police` refused; complementary accepted; omitted `role` = silence), TC-06 (uid omitted sub-game 1 / declared sub-game ≥ 2 / mismatched uid refused at handshake), TC-07 (both declare + disagree ⇒ refuse; one omits ⇒ play) — all green.
- [ ] TC-25 lock/pairing/uid vectors still green; spine green with real handshakes (both sides derive the same `game_id`/`game_uid`, no round-trip — US-MCP-001).
- [ ] Refusal channel test: a refused stranger receives a `receive_control` message carrying the code; local state unchanged (US-MCP-006).

### ST-07 — Turn frames + all-or-nothing validation (owner: IA → repo task T009)

Build (PLAN §5.7): `messages.py` — `TurnMessage`/`ControlMessage`/`AuditPayload` dataclasses with `to_wire`/`from_wire` (negotiation encoder omits `None`; turn optionals as explicit `null`s; unknown keys dropped on intake — the extension seam, FR-20), `validate_turn` (all decisions **before any state change**, FR-25), `validate_audit`, `assert_no_position_leak`. Unit tests per PRD §8.5.

**Definition of done:**
- [ ] TC-08 (missing `smell_grid` ⇒ refused, zero state change), TC-09 (stringified intensity refused; numeric accepted), TC-10 (uppercase commit refused), TC-11 (empty timestamp refused), TC-12 (unknown key tolerated and ignored) — green.
- [ ] TC-13 green: structural scan of the turn wire shape — no field carries a numeric position except the explicitly public `barrier_placed`/`capture_claim`; `hint` is text-only (NET-004, FR-26/27).
- [ ] TC-26 green: a Hebrew + astral-plane-emoji hint round-trips the wire byte-identical under `ensure_ascii=False`.
- [ ] Spine green with validated frames (a malformed frame from a scripted engine is refused without partial application).

---

## Phase D — M3: inbound delivery safety

### ST-08 — At-least-once inbox + fault injection (owner: IA → repo task T012)

Build (PLAN §5.8, §5.12): `inbox.py` — pure `delivery_decision` (the six-way pinned table; duplicates keyed on **commit**, not `(kind, step)`) + `deadline_decision` (pure; renews nothing; judged every lap) + `Inbox.offer` (absorb / equivocation-loud / buffer / apply-drain / discard / violation; `window` configurable, default 4, never 0 — a window-0 config is refused at load, FR-32) + `reset_for_subgame`. `faults.py` — `FaultyTransport` (deterministic: duplicate / reorder / drop-then-retry every nth turn message; `flush`).

**Definition of done:**
- [ ] TC-14 (exact duplicate absorbed; applied once; ledger unchanged), TC-15 (different commit for a played step ⇒ `Equivocation`, quarantined, loud), TC-16 (within-window out-of-order buffered and applied in sequence; beyond window rejected), TC-19 (duplicate/early push renews nothing; deadline judged on a flood lap) — green.
- [ ] TC-17 (first run): same seeded six-sub-game series, clean vs duplicate+reorder+drop-then-retry over `FaultyTransport` ⇒ **byte-identical outcome ledger** (NFR-1) — audit still stubbed; the final run with real audit lands in ST-09.
- [ ] Spine green; window-0 config refused test green.

---

## Phase E — M4 (loopback proof): mutual audit

### ST-09 — Mutual audit + TAMPERED sanction (owner: IA → repo task T008)

Build (PLAN §5.9): `audit.py` + `audit_physics.py` — `audit_records(records, played, terms)`: layer 1 re-hash every revealed record **with our own serializer** (any mismatch ⇒ step TAMPERED; verdict `{passed, verified_steps, failed_steps, skipped}`; one mismatch ⇒ technical loss, total sanction, **no repair path**, FR-29); layer 2 binding against the inbox `played` map (revealed == received, both directions, frontier-tolerant); layer 3 physics armed from the 14 terms (trail on-board, ≤ one orthogonal step, barrier quota, step ceiling — from the position trail, never the peer's move spelling). The stand-in engine's `audit_payload()` reveals all records + nonces + `result_claim`.

**Definition of done:**
- [ ] TC-20 green: full mutual audit clean ⇒ `{passed: true, …}`; then a one-byte mutation of one revealed record ⇒ TAMPERED, both sides score 0, no code path repairs it (US-MCP-004).
- [ ] TC-17 (final): clean vs fault-injected seeded series ⇒ byte-identical ledger **including audit verdicts** (US-MCP-003).
- [ ] Sealed step-0 record (identity declaration) rides inside `submit_audit.records` — there is no step-0 tool/turn on the surface (FR-19; SEC-008 record only — signing/metering stay out of scope, T013).
- [ ] `intent` field declared in sealed records; audit corroborates structurally (FR-42). Spine green.

---

## Phase F — M2: the real wire (FastMCP over localhost)

### ST-10 — FastMCP server (owner: IA → repo task T009)

Build (PLAN §5.15, §3): `mcp_server.py` — `build_server(inboxes)` with the four `@mcp.tool` handlers (validate, enqueue, return `{"ok": True}` — **no** await of game progress, no crypto, no state mutation, FR-8), **lazy `fastmcp` import** inside construction (NFR-5); `port_is_held(host, port)` — a **connect probe, never a trial bind** (FR-37); `preflight(cfg)` — runs the shared-layer guard scan and refuses to start on violation (FR-39) before any bind; `serve(cfg, inboxes, game_loop, peer_url)` — preflight → port check → server on a **daemon thread**, game loop on the caller's thread (FR-4); tools-only mode prints the kit's "TOOLS ONLY — no game loop" banner (a listener that never dials never plays, FR-3); mounted at `/mcp`; browser-shaped GET ⇒ `406` (the ready state, FR-9).

**Definition of done:**
- [ ] TC-01 green over the real server: all four tools listed under their exact names (`receive_control` present).
- [ ] TC-22 green: handler enqueue-and-return p99 < 5 ms on localhost (benchmark in `tests/contract/mcp/`); static scan of handler bodies ⇒ zero blocking/crypto calls (scan lives in `scripts/check_shared_layer.py`, ST-14 — the handler-subset runs here via a focused test).
- [ ] Preflight test: a deliberately injected guard violation (test fixture) ⇒ server refuses to bind (exit code 5 path).
- [ ] 406 probe test: browser-shaped GET ⇒ 406; MCP `initialize` POST ⇒ real `protocolVersion` answer (TC-23 partial).
- [ ] `uv run pytest tests/contract/mcp` green with `fastmcp` installed; the zero-dep spine still green without importing `fastmcp`.

### ST-11 — FastMCP client + two-process localhost smoke (owner: IA → repo task T009)

Build (PLAN §5.16): `mcp_client.py` — `McpChannel` implementing `PeerChannel`: **one session held across the series** (FR-30) on a **private event loop in a daemon thread**, synchronous facade (the game loop stays async-free), per-call timeout from config; on session-terminated ⇒ tear down, re-establish **once**, retry within the original deadline, else `PeerUnreachable` (FR-31); the `payload`/`message` asymmetry applied at the call site. `probes.py` — `edge_answers`, `classify_probe` (pure), `diagnose`. Role `entry.py` real mode: builds `McpChannel(peer_url)` + serves + runs the facade (two processes).

**Definition of done (SC-1, `local_mcp_smoke`):**
- [ ] TC-21 green: **two independent local processes** (one from `police_repo`, one from `thief_repo`, separate config areas, FR-38) on `localhost` complete the full surface — handshake, six sub-games, mutual audits — **without a public endpoint and without an opponent URL**.
- [ ] TC-02 green over real HTTP: calling `submit_audit` with an argument named `message` ⇒ schema error (the asymmetry asserted, not assumed, FR-7).
- [ ] US-MCP-001/002 over HTTP: handshake with same-derived ids; a legal turn returns `{"ok": True}` in µs while the nonce stays secret (FR-8, US-MCP-002).
- [ ] `reference_v3_contract` gate: the four-tool surface, argument asymmetry, turn keys/shapes, locked-model declaration/refusal, thief-first order, no step-0 — all asserted against the live local server (`tests/contract/mcp/`), no real opponent required.
- [ ] Spine (loopback) still green; full repo gates green.

---

## Phase G — M4 (system): session faults & recovery

### ST-12 — Session faults + recovery suite (owner: IA → repo task T012 + T022 local)

Build: `tests/integration/test_session_faults.py` + `tests/integration/test_recovery_matrix.py` (T022 write set) — session torn down at a sub-game boundary (rolling-window topology) ⇒ re-established once, series continues (TC-18, FR-31); recovery matrix over loopback and over localhost HTTP: loss, duplicate, reorder, stale step, disconnect, slow response, crash-then-restart — each with a **deterministic outcome** (seeded, injected, no flake); the ledger is byte-identical across clean/faulted runs of the same seed; audit binds reveals to stored live commitments and rejects fabricated/missing/impossible/mutated histories.

**Definition of done:**
- [ ] TC-18 green; recovery-matrix cases green with deterministic outcomes (T022 acceptance criteria 1–4, local).
- [ ] A dead session never forks state and never costs the game (G4): every fault case ends in either a settled series or a rule-classified technical loss — never a hang (FR-34: no indefinite wait).
- [ ] Spine + full suite green.

---

## Phase H — M5: league readiness & system proof

### ST-13 — Tunnel readiness discipline (owner: IA → repo tasks T009/T022)

Build (PLAN §5.17): `readiness.py` — (1) probe classification: browser-shaped GET + MCP `initialize` POST ⇒ `406` = **ready**, `502` = edge up / nothing behind (peer not started or no ingress — prove your *own* path), `421` = Host header not rewritten (fix **at the tunnel**: ngrok `--host-header=rewrite` / Cloudflare `originRequest.httpHostHeader` — never in code), `404` = wrong path (peers mount at `/mcp`), 30x = forwarder not peer; (2) **loopback nonce proof**: bind a throwaway listener on the series port, fetch your own public hostname through the tunnel, demand back a nonce you generated (refuses to run if the port is already held); (3) `--await-peer`: poll the opponent's edge (any HTTP answer, 406 included) for one handshake budget before the first greeting — the same budget the arrived peer gets (FR-36, US-MCP-005). CLI wiring in `entry.py`.

**Definition of done:**
- [ ] TC-23 green: probe suite classifies 406-ready, 421-with-tunnel-fix-text, 502, MCP `initialize` answered; `classify_probe` unit-tested as a pure function.
- [ ] Loopback nonce proof runs against a local stand-in tunnel (loopback hostname) and fails loudly on a held port (TC-23/US-MCP-005).
- [ ] `--await-peer` budget polling test: a cold-started edge within budget is not read as "opponent never arrived"; beyond budget it is (one answer on both sides).
- [ ] SC-5 satisfied for the local part; the public-endpoint criterion stays marked **G-LIVE-blocked** (not run, not faked).

### ST-14 — Guards, cross-repo sync, Stage-2 system proof (owner: IA → repo task T022)

Build: `guards.py` (shared-layer scan, reusable by preflight) + repo scripts `scripts/check_shared_layer.py` (refuses to start on violation, FR-39: no network import outside `mcp_server`/`mcp_client`/`probes`/`readiness`; no `fastmcp` outside the two transport modules; no module-level mutable state in `common/transport/`; no role-code import into `common/`; one canonical hash path) and `scripts/check_common_sync.py --sibling <path>` (0 differing files across `common/` — SC-6, the KPI subject ADR-005 was waiting for). Wire the guard into `mcp_server.preflight`. Then the **Stage-2 system proof** (PRD M4): the full run — two processes, one per repo, `localhost`, six sub-games, mutual audits, fault-injected re-run, vector suite, contract suite — as one gated script `scripts/stage2_system_proof.py` (or a pytest marker) producing a single pass/fail ledger.

**Definition of done:**
- [ ] TC-24 green: `common/` sync check = 0 differing files; source scan clean; preflight refuses on an injected violation.
- [ ] SC-1…SC-7 (local criteria) all evidenced: SC-1 two-process smoke, SC-2 reference-v3 surface 15/15, SC-3 byte-identical faulted ledger, SC-4 golden vectors 100%, SC-5 readiness tooling executable, SC-6 separation by construction, SC-7 no numeric-position path / LLM never decides (TC-13/TC-27 evidence).
- [ ] `uv run python scripts/run_quality_gates.py` + `uv run pytest` (85% coverage incl. `common`) green in **both** repos.
- [ ] Handoff: the system-proof ledger (per-TC results + seeds + commit SHAs of both repos).

### ST-15 — Live interop + public endpoint (owner: IA, authorized by ORC) — **gate: G-LIVE**

Build: nothing new in the shared layer — this is execution of the readiness discipline against a real tunnel and a real/kit opponent: authorize public endpoint exposure (human gate), stand up tunnels with Host-header rewrite, run the readiness checklist (SC-5 public part), then a full **uncounted** six-sub-game series against the stock kit sparring peer (terms paired per PRD §9.2 — `setting: "Haifa"` for the kit pairing) and/or a second human team, mutual audits clean in both role directions, before any counted play is scheduled (T022 live criteria).

**Definition of done:**
- [ ] G-LIVE satisfied and human-authorized (endpoint exposure + cross-team terms + start time).
- [ ] Full uncounted live series settles with clean mutual audits in both directions; any compatibility failure (report-layout, scent-profile, tie-profile, draft-vs-send) detected **before** counted play.
- [ ] `live_interop` + `public_endpoint` gates recorded with evidence (probe logs, ledgers, artifact paths).

---

## TC coverage progression

| TC | Covered in | TC | Covered in | TC | Covered in |
|---|---|---|---|---|---|
| TC-01 | ST-02, ST-10 | TC-10 | ST-07 | TC-19 | ST-08 |
| TC-02 | ST-02, ST-11 | TC-11 | ST-07 | TC-20 | ST-09 |
| TC-03 | ST-06 | TC-12 | ST-07 | TC-21 | ST-11 |
| TC-04 | ST-06 | TC-13 | ST-07 | TC-22 | ST-10 |
| TC-05 | ST-06 | TC-14 | ST-08 | TC-23 | ST-10, ST-13 |
| TC-06 | ST-06 | TC-15 | ST-08 | TC-24 | ST-14 |
| TC-07 | ST-06 | TC-16 | ST-08 | TC-25 | ST-04 |
| TC-08 | ST-07 | TC-17 | ST-08 (first), ST-09 (final) | TC-26 | ST-07 |
| TC-09 | ST-07 | TC-18 | ST-12 | TC-27 | ST-03 |
| — | — | — | — | TC-28 | ST-03, ST-06 |

KPI "requirement-to-test coverage of FR-1…FR-42 = 100%" — see PLAN §14 (the FR→TC→stage table); the ST-14 handoff must include it complete.

## Stage definition of done (stage 2 gate)

Stage 2 is complete when, with evidence in the handoffs:

1. ST-01…ST-14 are `done` (ST-15 tracked separately behind `G-LIVE`).
2. The spine test and the Stage-2 system proof pass in **both** repositories on the same commit pair (sync check = 0 differing files).
3. All PRD success criteria SC-1…SC-7 hold for their local scope (SC-5's public part waits on G-LIVE).
4. The repository gates (`ruff`, `pytest` ≥ 85% incl. `common`, quality-gates script, line cap, secrets, planning graph) pass in both repos.
5. No draft artifact (canonicalization, payload schema, profile values) is labeled or used as official (PRD C1/C2; OPEN-001/007 remain OPEN).
6. The repo `TODO.md` is reconciled: T008/T009/T012/T022 statuses reflect the stage evidence; O-1/O-2 closed.
