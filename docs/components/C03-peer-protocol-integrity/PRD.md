---
artifact: component-prd
id: PRD-C03
component: C03
status: draft
shared: true
owner: orchestrator
updated: 2026-08-16
---

# C03 — Peer Protocol & Integrity

## Purpose

Own the symmetric FastMCP server/client surface each peer exposes and calls, the natural-language channel rule, and the single Commit-Reveal/audit path that makes every accepted step cryptographically verifiable. This is the interoperability boundary: it is the one component whose output must be byte-identical between two independently written implementations for a match to be legal at all.

## Requirements owned (primary)

NET-001…004 (symmetric FastMCP roles, public reachability, free-form natural-language channel, prohibition on a numeric-position substitute); SEC-001…009 (Commit-Reveal protocol, protocol order, commitment binding, Nonce freshness/secrecy, mutual audit, TAMPERED sanction, truthful Capture Claim response, signed Step 0, token-consumption monitoring). 13 requirements total.

## Requirements consumed / affected

- NET-005 (C04): C04 owns the deadline/retry/technical-loss behavior; this component only carries the timestamp/expiry fields on the envelope.
- SEC-010 (system): secret handling is a repository-wide prohibition, not this component's behavior, though this component's OAuth-adjacent Step 0 material must respect it.
- REPORT-005…009 (C06): reports embed this component's verified commitments and audit results; C06 does not redefine them.
- OBS-005, OBS-006 (C05): Replay re-verifies this component's commitments; the verification algorithm itself lives here.

## Observable behavior

- Each peer acts simultaneously as FastMCP server and client (NET-001); each side actively dials the other, so neither peer is purely passive. For league play the server is reachable through a public address, with localhost-only allowed during early development (NET-002).
- The first and default wire adapter this component implements is the `reference-v3` profile recorded in `planning/contracts/CT-03-peer-wire.md`: four tools with the exact argument-name asymmetry, the required turn-message keys including `smell_grid`, locked-model declarations carried outside the closed signed-terms set, `info_mode: belief`, unbound smell behavior, and the thief-first turn-order convention. This is an engineering profile behind an adapter boundary, not an official schema.
- The verbal channel is free-form natural language and is never replaced by a direct numeric-position protocol (NET-003, NET-004).
- Every game step is protected by a SHA-256 Commit-Reveal protocol in the order Commit, Acknowledge, Reveal, then Final Reveal/Audit at game end (SEC-001, SEC-002); the commitment binds at least State, Move, Intent, and Nonce (SEC-003) using a fresh, secret-until-audit Nonce (SEC-004).
- At game end, both sides perform a complete mutual log audit, reveal all Nonces, and recompute commitments (SEC-005); a single hash mismatch is marked TAMPERED with no retrospective repair (SEC-006).
- During a Capture Claim the responding side tells the truth; a false declaration or denial causes immediate disqualification (SEC-007).
- Before the first move, a signed Step 0 records the required hardware/model/version/team/commit fields (SEC-008); LLM token consumption is monitored, cryptographically locked, and reported (SEC-009).

## Inputs

Locally selected legal action and hint (from C02, via CT-02); the peer's incoming MCP frames; the locked `config/game.json`.

## Outputs

Sent/received MCP frames; commitment, acknowledgement, and reveal records; a verified audit result consumed by C06 (via CT-06) and re-displayed by C05.

## Invariants

- One canonical hashing implementation; no second, informally-defined hash path.
- A Nonce is never logged or transmitted before audit.
- A TAMPERED verdict is final — no retrospective repair converts it back to a clean result.

## Constraints

- No game-decision logic in this component; it transports and verifies, it does not decide.
- Exact cross-peer canonical bytes (nonce placement, Unicode escaping, separators, signature scope) remain an internal, explicitly-labeled-non-official draft (`planning/contracts/CT-04-canonical-bytes.md`) until OPEN-007 resolves.

## Failure cases

- Request expiry: this component supplies the timestamp/expiry fields; C04 owns the resulting retry/technical-loss decision (NET-005).
- Exact duplicate frame: absorbed, prior result returned without reapplying state.
- Conflicting duplicate: quarantined as equivocation/tamper evidence.
- Hash/audit failure: TAMPERED, scoring path per SEC-006.

## Edge cases

- Bounded reordering within the configured window (buffered until predecessor arrives; rejected beyond policy).
- A session termination mid-turn (re-established once within the original deadline, obligation not renewed).
- A capture claim response that is truthful about a non-capture (SEC-007's negative case).

## Acceptance scenarios

- [ ] The full Commit → Acknowledge → Reveal → Final Reveal/Audit sequence is exercised end-to-end with a clean run producing Verified OK. {#commit_reveal_happy_path}
- [ ] A one-byte mutation to any committed field deterministically produces TAMPERED with no repair path. {#tamper_detection}
- [ ] The byte-level primitives this component owns — canonical serialization, the commit construction, and the terms/uid signatures built on it — reproduce the available golden vectors during the task that builds them, not only at the final gate. {#early_byte_vectors}
- [ ] Cross-peer canonical byte fixtures for the *official* envelope pass only after OPEN-007 resolves; until then, only the draft contract's differential tests run. {#cross_peer_vectors}
- [ ] A local two-process FastMCP smoke test completes without a public endpoint. {#local_mcp_smoke}
- [ ] The `reference-v3` compatibility surface in CT-03 is exercised locally end to end, with no real opponent URL required. {#reference_v3_contract}
- [ ] Public-endpoint reachability is exercised only once `G-LIVE` is satisfied. {#public_endpoint}

## Relevant contracts

`planning/contracts/CT-01-game-state.md` (consumer); `planning/contracts/CT-02-strategy-decision.md` (consumer); `planning/contracts/CT-03-peer-wire.md` (owner); `planning/contracts/CT-04-canonical-bytes.md` (owner); `planning/contracts/CT-06-verified-result.md` (co-owner with C04).

## Relevant OPEN/input gates

- OPEN-007 — `blocks: criterion` on `{#cross_peer_vectors}` only, and it stays officially OPEN. Local Commit-Reveal primitives (`{#commit_reveal_happy_path}`, `{#tamper_detection}`) and the early golden-vector proof (`{#early_byte_vectors}`) are unaffected: reproducing a published non-authoritative vector demonstrates our bytes match a known peer, which is not the same as adopting an official envelope.
- OPEN-006 — Step 0 signing-key procedure; `blocks: criterion` on the final signed-Step-0 provisioning criterion, not on building the Step 0 record structure itself.
- `G-LIVE` — `blocks: criterion` on `{#public_endpoint}` only; `{#local_mcp_smoke}` is unaffected.

## Definition of Done

All acceptance scenarios pass; the integrity module has exactly one canonical hashing path; nonce/tamper/replay/physics audit tests plus the secret scanner pass; `check_planning_graph.py` shows NET-*/SEC-001…009 owned only here.
