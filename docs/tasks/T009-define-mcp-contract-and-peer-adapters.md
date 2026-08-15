---
id: T009
status: blocked
priority: P0
implements:
  - NET-001
  - NET-002
  - NET-003
  - NET-004
depends_on:
  - T001
  - T003
parallel_safe: true
claimed_by:
claim_expires_at:
write_set:
  - src/police_peer/transport/mcp_server.py
  - src/police_peer/transport/mcp_client.py
  - src/police_peer/transport/contracts.py
  - tests/contract/mcp/
  - tests/integration/test_two_process_smoke.py
risk: high
---

# T009 — Define Mcp Contract And Peer Adapters

## Expected outcome

Thin FastMCP server/client adapters expose the approved peer contract, preserve free-form language, and can operate through a configured public endpoint.

## Requirements implemented

- `NET-001`
- `NET-002`
- `NET-003`
- `NET-004`

## Relevant context

The official material fixes FastMCP/MCP behavior but does not supply a complete attached wire schema. Do not register guessed fields as official; record the negotiated contract.

## Constraints

- Do not edit the canonical PRD.
- Do not silently redefine the repository PLAN or task dependencies.
- Do not widen scope or treat a derived design decision as a source requirement.
- Edit only the declared write set; request an orchestrator-approved change before crossing it.
- Escalate requirement conflicts, missing official inputs, and newly discovered work.

## Acceptance criteria

- [ ] Server and client run in the same peer process while state remains role-local.
- [ ] Tool discovery and contract mismatch diagnostics fail before game start.
- [ ] Natural-language hints remain free-form and no direct numeric-position side channel exists.
- [ ] Endpoint, tunnel, request timeout, and retry limits come from configuration.
- [ ] Contract tests exercise two independent processes and reject incompatible role/sub-game/config identifiers.

## Verification

- `uv run pytest tests/contract/mcp tests/integration/test_two_process_smoke.py`
- `uv run ruff check src/police_peer/transport tests/contract/mcp tests/integration/test_two_process_smoke.py`

## Implementation plan

To be completed immediately before execution.

## Handoff contract

Report files changed, tests executed, exact test results, decisions made, deviations, blockers, and newly discovered work. Include command output or artifact paths sufficient for the orchestrator to validate every acceptance criterion.

## Result and evidence
