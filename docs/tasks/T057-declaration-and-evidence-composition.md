---
artifact: task
id: T057
title: Compose real evidence into the declaration and result
status: done
owner: orchestrator
component: C06
depends_on: [T056]
related_requirements: [REPORT-005, REPORT-006, OBS-006, LEAGUE-002, LEAGUE-003]
related_decisions: [ADR-013]
related_contracts: [CT-08]
write_set:
  - src/police_peer/evidence/git_revision.py
  - src/police_peer/evidence/identity_source.py
  - src/police_peer/reporting/kit_bundle.py
  - src/police_peer/sdk.py
  - src/police_peer/runner.py
  - src/police_peer/cli.py
---

# T057 — Declaration and evidence composition

## Goal

The Wave-1 declaration named a bare `group_id` for each side. This task assembles a real,
verifiable `GroupIdentity` for our own side from live evidence (private config, runtime
summary, the exact HEAD commit, and the pairing history's counted-match count), attaches it to
the declaration, and gates counted play on that evidence being complete and honest.

## What was built

* `evidence/git_revision.py::head_commit`/`require_head_commit` — the exact commit that played
  (App. E rule 53), read from `.git/HEAD` and its referenced ref (loose or packed) with **no
  subprocess call**, so evidence collection never depends on a `git` binary being on PATH.
* `evidence/identity_source.py::build_identity` — assembles a `GroupIdentity` from
  `common.config.PrivateConfig` (the new App. B §4 private sections), raising a distinctly
  named `IdentitySourceError` for each missing required field.
* `evidence/identity_source.py::assert_counted_ready` — refuses **before any game starts** when
  counted play could not be honestly reported: an uncomputable config digest, an incomplete
  identity, no configured Step-0 signer, unknown counted token usage, or a pairing the league
  guard rejects. Warm-up never refuses on any of these.
* `sdk.create_peer` gained `declared_private`, `repo_root`, and `signer_configured` parameters
  and calls `assert_counted_ready` once, before the `PeerFacade` is even constructed.
* `cli.py` gained `--group-code`, `--members`, `--repo-cop-url`, `--repo-thief-url`, and
  `--public-url`, all optional, overriding the private TOML.
* `runner.py::_publish_kit` builds our own signed group block (`kit_identity.group_block`) and
  passes it as half of the declaration's `groups` list when a complete identity is available;
  it falls back to Wave-1's existing bare `{"group_id": ...}` behaviour otherwise — never a
  fabricated value.

## Deviation recorded (see ADR-013 "Consequences")

The opponent's identity block in a published declaration currently carries only
`{"group_id": <opponent>}` in production, because this wave's write set does not include a
place to persist the opponent's declared identity captured during the per-sub-game handshake
(`src/police_peer/wire/negotiate_per_subgame.py` discards the raw greeting after verifying it,
and the natural place to store it, `common/transport/opponent_pin.py`, is a frozen Wave-1/2
`common/` module outside this task's write set). `tests/integration/test_declaration_completeness.py`
proves the composition is correct once both sides' blocks are supplied — the remaining gap is
purely "where does the opponent's greeting-declared identity get stored for later use",
tracked as follow-up work rather than solved by touching a prohibited module.

## Acceptance

```
uv run ruff check .
uv run pytest
uv run python scripts/run_quality_gates.py
```
