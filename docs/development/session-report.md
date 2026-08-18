---
artifact: development-record
id: SESSION-2026-08-18
status: informational
owner: orchestrator
updated: 2026-08-18
---

# Development session record — 2026-08-18

A record of one supervised multi-agent working session that produced the
documentation-planning consolidation on `master` and the FastMCP transport work
on `feature/mcp`. It contains aggregate cost and test accounting only: no
secrets, credentials, tokens, account identifiers, generation identifiers, or
personal data. This is process metadata, not a game requirement or contract.

## Model roles

A Claude Code session acted as the supervisor (Git, reasoning, task
decomposition, validation, and the human gates). Substantive bounded work ran on
heterogeneous non-Claude models through the Pi harness over OpenRouter:

- **Writer** — `google/gemini-3.7-flash` (documentation reconciliation).
- **Escalated writer** — `z-ai/glm-5.2` (Thief role-owned documents).
- **Independent reviewer** — `deepseek/deepseek-v4-pro` (read-only).
- **Cross-repository final verifier** — `z-ai/glm-5.2` (read-only).

## Worker cost (OpenRouter, both repositories combined)

The figures below are the authoritative OpenRouter billing for the non-Claude
workers. The Claude Code supervisor's own usage is billed separately and is not
included here.

| Model | Calls | Cost (USD) |
|---|---|---|
| `deepseek/deepseek-v4-pro` | 147 | 2.44 |
| `z-ai/glm-5.2` | 28 | 1.20 |
| `google/gemini-3.7-flash` | 105 | 0.73 |
| **Total** | **280** | **4.38** |

- Tokens: about 17.6M prompt, 0.38M completion, 0.31M reasoning.
- Two calls were cancelled (a review process was interrupted and re-dispatched);
  the cancelled attempts are included in the total above.
- The reviewer and verifier dominate the cost: read-only review at high and
  extra-high reasoning over large diffs is the expensive part, not the writing.
- OpenRouter routed these models across several inference providers; the split
  above is by model, which is what the roles map to.

## Work delivered

- Consolidated `docs/documentation-fix` and `docs/operational-conventions` onto
  `master` by reconstruction (no implementation snapshot), then retired both
  branches. Reviewed by DeepSeek and cross-verified by GLM: no blocking issues.
- Merged `master` into `feature/mcp`; regenerated the scent profiles clean-room
  from the M-01 §B book specification (no third-party kit code remains); adopted
  the FastMCP 3.4 runtime baseline; implemented the real FastMCP server and
  client (ST-10 / ST-11) replacing the stubs.

## Tests and simulations

- Test suite: 57 test files across `tests/unit/{domain,scent,transport,wire}`,
  `tests/integration`, and `tests/contract`. The full suite is 567 tests and
  passes in both repositories, from fresh clones with `uv sync --locked`.
- New real-HTTP contract suite `tests/contract/mcp/test_local_mcp_smoke.py`:
  the `/mcp` edge answers a browser GET with `406`; all four tools list under
  their exact names; `submit_audit(message=…)` is rejected over HTTP; and the
  full six-sub-game series settles over localhost HTTP with both peers agreeing
  on `game_id` / `game_uid`.
- Two-process localhost simulation: a `police_repo` peer and a `thief_repo` peer,
  each serving its own FastMCP server and dialing the other over real HTTP with
  no public endpoint, both exit 0 and complete six sub-games with mutual audits
  and complementary outcomes. Reproduced from fresh clones.

## Deterministic verification

Both repositories: ruff clean, 7 of 7 repository quality gates, planning-graph
0 issues, `uv.lock` coherent (FastMCP 3.4.7). Independent DeepSeek review and
GLM cross-repository verification each reported no blocking issues; the review's
non-blocking transport-robustness findings were applied.
