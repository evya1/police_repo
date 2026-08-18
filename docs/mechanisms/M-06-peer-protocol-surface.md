---
artifact: mechanism-prd
id: M-06
component: C03
status: draft
shared: true
owner: orchestrator
updated: 2026-08-16
---

# M-06 — Peer Protocol Surface

## Why this mechanism has its own PRD

This is the interoperability boundary itself — the FastMCP tool/envelope surface and the natural-language rule that let two independently written peers actually talk. It is also the anchor for the league-kit adapter described in `planning/interop/LEAGUE_COMPATIBILITY.md`, so it needs to be addressable on its own rather than folded into the general C03 PRD.

## Governing requirements

NET-001 (symmetric server/client roles via FastMCP), NET-002 (public reachability for league play; localhost allowed only during early development), NET-003 (free-form natural-language channel), NET-004 (prohibition on a direct numeric-position substitute for the language channel).

## Specified behavior (binding)

- Each peer acts simultaneously as MCP server and client, exposing and calling tools implemented with FastMCP (NET-001).
- For league play, each peer's server is reachable through a public address via tunneling or an equivalent mechanism; localhost-only operation is permitted only during early development, never for a counted match (NET-002).
- The verbal channel between agents is free-form natural language (NET-003) and is never replaced by a direct numeric-position protocol, even as an internal shortcut (NET-004).

## Surface shape (negotiated, non-official pending OPEN-001/OPEN-007)

The exact tool names, request/response envelope fields, and versioning scheme are this component's own engineering choice, exercised locally and versioned so a later official schema can be adopted without breaking the local contract. They are not asserted as official.

## First implemented profile — `reference-v3` (engineering decision, non-official)

The first and default interoperability adapter this project implements is `wire_shape: reference-v3`, an operational convention recorded in `ADR-004` (`docs/decisions/`) and detailed in the compatibility surface in `planning/contracts/CT-03-peer-wire.md`. It is not a course requirement and not an official schema. Adopting it does not resolve OPEN-001 or OPEN-007.

The compatibility surface this adapter must eventually meet is stated once, in CT-03, so it is not restated here. In summary it comprises: the four tool names (`negotiate`, `receive_turn`, `submit_audit`, `receive_control`), the argument-name asymmetry between them, the required turn-message keys including `smell_grid`, the locked-model declarations carried outside the closed signed-terms set, `info_mode: belief`, unbound smell behavior, and the reference-v3 turn-order convention in which the thief takes the first game turn.

Any officially compliant peer remains a fully valid opponent. `reference-v3` is one profile behind an adapter boundary, not this component's internal architecture.

## Local vs. live testing

- **Local**: two processes on `localhost`, each acting as both server and client, exercising the full tool surface, deadline/retry behavior (via C04), and Commit-Reveal (via M-05) without any public endpoint and without a real opponent URL. This is always available and does not depend on `G-LIVE`.
- **Live/public**: requires `G-LIVE` (a real opponent, agreed terms, working tunnel). Only the public-reachability criterion is gated; the tool surface and the `reference-v3` profile contract are proven locally first.

Tunnels, live pairing, and endpoint selection are not designed here — that remains PLANQ-006 and later tasks.

## Acceptance scenarios

- [ ] A local two-process smoke test exercises the full tool surface over `localhost`, with each side actively participating as both server and client. {#local_mcp_smoke}
- [ ] The verbal channel accepts free-form text and rejects any code path that substitutes a raw coordinate pair for it. {#no_numeric_substitute}
- [ ] The `reference-v3` compatibility surface recorded in CT-03 is exercised locally: exact tool and argument names, required turn-message keys, locked-model declaration and refusal behavior, and turn order. {#reference_v3_contract}
- [ ] Public-endpoint reachability is exercised only once `G-LIVE` is satisfied. {#public_endpoint}

## Owning task

T009 (`NET-001…004`), depends on T003. Public-endpoint criterion gated by `G-LIVE`; the local smoke test and the `reference-v3` contract criterion are unaffected and need no opponent URL.
