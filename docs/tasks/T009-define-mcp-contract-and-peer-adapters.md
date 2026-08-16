---
id: T009
status: blocked
priority: P0
task_type: component
component: C03
optional: false
implements:
  - NET-001
  - NET-002
  - NET-003
  - NET-004
context_files:
  - docs/components/C03-peer-protocol-integrity/PRD.md
  - docs/components/C03-peer-protocol-integrity/PLAN.md
  - docs/mechanisms/M-06-peer-protocol-surface.md
  - docs/contracts/CT-03-peer-wire.md
  - docs/decisions/ADR-004-kit-first-interoperability-profile.md
read_set: []
depends_on:
  - T003
gates:
  - id: G-LIVE
    kind: input_gate
    scope: public_endpoint
    blocks: criterion
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

Thin FastMCP server/client adapters implement the `reference-v3` peer contract as the first and default interoperability profile, preserve free-form language, run as two local processes with no opponent URL, and can later operate through a configured public endpoint.

## Requirements implemented

- `NET-001`
- `NET-002`
- `NET-003`
- `NET-004`

## Relevant context

The official material fixes FastMCP/MCP behavior but does not supply a complete attached wire schema, and OPEN-001/OPEN-007 stay open. Do not register guessed fields as official.

`ADR-004` selects `reference-v3` as the first and default adapter profile, and `docs/contracts/CT-03-peer-wire.md` records its exact currently verified surface. That profile is a human-approved engineering choice evidenced by a non-authoritative compatibility target — implement it as a profile behind the adapter boundary, never as an official schema, and keep a non-kit officially compliant peer a valid opponent.

The entire contract is provable with two local processes. A real opponent URL, a tunnel, or a public endpoint must **not** block this task; endpoint and tunnel selection remain PLANQ-006 and later tasks.

## Gates

- `G-LIVE` (`input_gate`, `blocks: criterion`) — the task may be claimed and implemented now; only the acceptance criterion scoped `public_endpoint` waits. The `reference-v3` contract and the local two-process smoke test are unaffected and require no opponent.

## Constraints

- Do not edit the canonical PRD.
- Do not silently redefine the repository PLAN or task dependencies.
- Do not widen scope or treat a derived design decision as a source requirement.
- Edit only the declared write set; request an orchestrator-approved change before crossing it.
- Escalate requirement conflicts, missing official inputs, and newly discovered work.

## Acceptance criteria

- [ ] Server and client run in the same peer process while state remains role-local, and this side actively dials the peer as well as serving it — a peer that only listens never plays.
- [ ] The four `reference-v3` tools are exposed and called under their exact names: `negotiate`, `receive_turn`, `submit_audit`, `receive_control`. The first three are required; `receive_control` touches no game state and is never sealed or scored.
- [ ] The argument-name asymmetry is preserved exactly: `submit_audit` takes `payload`; `negotiate`, `receive_turn`, and `receive_control` take `message`. A test asserts the asymmetry rather than assuming it.
- [ ] Turn messages carry the required keys `step`, `sender`, `hint`, `smell_grid`, `commit`, `timestamp`; `smell_grid` is present with `{'r,c': number}` values and a stringified intensity is refused. A missing required key is refused, never defaulted; an unknown key is tolerated and ignored; every decision is made before any state change.
- [ ] Selected-profile declarations for `scent_model`, `wire_shape`, `info_mode`, and `smell_binding` are sent as document hashes at negotiate time, outside the closed signed-terms set, and refusal fires only when both peers declare a family and disagree — silence on either side is never refusal.
- [ ] `info_mode: belief` is declared and structurally honored: the rival's position never crosses the wire.
- [ ] The `reference-v3` turn-order convention is implemented and asserted — the thief takes the first game turn — with a diagnostic that names a turn-order disagreement rather than reporting a bare timeout. `{#reference_v3_contract}`
- [ ] Tool discovery and contract mismatch diagnostics fail before game start.
- [ ] Natural-language hints remain free-form and no direct numeric-position side channel exists.
- [ ] Endpoint, tunnel, request timeout, and retry limits come from configuration; no value is required to be a real opponent's for the local suite to pass.
- [ ] Contract tests exercise two independent local processes with no public endpoint and no opponent URL, and reject incompatible role/sub-game/config identifiers. `{#local_mcp_smoke}`
- [ ] Public-endpoint reachability over a real or simulated tunnel is exercised only once `G-LIVE` is satisfied; the local smoke test above does not require it. `{#public_endpoint}`

## Verification

- `uv run pytest tests/contract/mcp tests/integration/test_two_process_smoke.py`
- `uv run ruff check src/police_peer/transport tests/contract/mcp tests/integration/test_two_process_smoke.py`

## Implementation plan

To be completed immediately before execution.

## Handoff contract

Report files changed, tests executed, exact test results, decisions made, deviations, blockers, and newly discovered work. Include command output or artifact paths sufficient for the orchestrator to validate every acceptance criterion.

## Result and evidence
