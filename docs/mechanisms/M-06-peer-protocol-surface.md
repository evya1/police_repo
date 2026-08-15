---
artifact: mechanism-prd
id: M-06
component: C03
status: draft
shared: true
owner: orchestrator
updated: 2026-08-15
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

## Local vs. live testing

- **Local**: two processes on `localhost`, exercising the full tool surface, deadline/retry behavior (via C04), and Commit-Reveal (via M-05) without any public endpoint. This is always available and does not depend on `G-LIVE`.
- **Live/public**: requires `G-LIVE` (a real opponent, agreed terms, working tunnel). Only the public-reachability criterion is gated; the tool surface itself is proven locally first.

## Acceptance scenarios

- [ ] A local two-process smoke test exercises the full tool surface over `localhost`. {#local_mcp_smoke}
- [ ] The verbal channel accepts free-form text and rejects any code path that substitutes a raw coordinate pair for it. {#no_numeric_substitute}
- [ ] Public-endpoint reachability is exercised only once `G-LIVE` is satisfied. {#public_endpoint}

## Owning task

T009 (`NET-001…004`), depends on T003. Public-endpoint criterion gated by `G-LIVE`; local smoke test is unaffected.
