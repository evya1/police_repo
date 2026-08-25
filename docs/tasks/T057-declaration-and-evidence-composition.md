---
artifact: task
id: T057
title: Compose declarable evidence into the kit declaration; refuse counted play by name
status: done
priority: P0
task_type: integration
optional: false
owner: orchestrator
component: C06
depends_on: [T013, T056]
related_requirements: [REPORT-007, SEC-008, SEC-010, LEAGUE-001]
related_decisions: [ADR-013]
related_contracts: [CT-08]
write_set:
  - src/police_peer/evidence/git_revision.py
  - src/police_peer/evidence/identity_source.py
  - src/police_peer/league/readiness.py
  - src/police_peer/wire/identity_config.py
  - src/police_peer/wire/config.py
  - config/game.toml.example
---

# T057 — Declaration and evidence composition

## Goal

Assemble the group identity a counted declaration owes — members, repos, endpoints, hardware,
model, commit, prior counted-game count — from real sources only, and refuse counted play by
name when a required piece is missing.

## What was built

* `evidence/git_revision.py` — reads `.git/HEAD` and, when needed, `packed-refs` directly, so
  the commit that played is recorded without spawning a subprocess (App. E rule 53).
* `evidence/identity_source.py` — assembles a `GroupIdentity` from the private TOML, the real
  host, the commit reader, and the pairing history the league guard already maintains.
* `league/readiness.py::assert_counted_ready` — the composition-root gate. Checked, each named
  in its own refusal: the team code confirmation, the pre-game declaration (via
  `IdentityError`), the negotiated terms (so a config digest exists), and unknown token usage
  for any counted step.
* `wire/identity_config.py` — the App. B §4 private-TOML sections (`[game]`, `[network]`,
  `[llm]`, `[email]`), all optional so a warm-up never needs a filled-in declaration.
* `league/runtime_evidence.py`, `sdk.py`, and `runner.py` — the production composition path.
  Counted readiness is resolved before the MCP server starts; the verified public identity
  subset is carried in every greeting, the opponent's actual subset is retained, and the two
  honest blocks are projected into the declaration. An opponent URL is never relabelled as our
  own public endpoint.

## Verification

```
uv run pytest tests/unit/evidence/test_git_revision.py       11 passed
uv run pytest tests/unit/league/test_counted_readiness.py    10 passed
uv run pytest tests/unit/test_private_config_identity.py      7 passed
uv run pytest tests/integration/test_declaration_completeness.py   3 passed
uv run pytest tests/unit/test_runner_composition.py                production refusal covered
uv run python scripts/smoke_replay_integration.py --config config/game.json \
      --private-config config/game.toml.example --artifact-root /tmp/w2 --json
python tools/check_artifacts.py /tmp/w2/kit/<uid>            -> ALL ARTIFACT CHECKS PASS
python -m sparring.cli replay   /tmp/w2/kit/<uid> --expect-clean -> 6 verified, 0 tampered
```

## Notes

`git_revision.py` deliberately does not shell out: a subprocess would inherit the caller's
environment and working directory and could hang inside a turn budget, and reading two small
files under `.git` cannot. A test monkeypatches `subprocess.run`/`check_output`/`Popen` to raise
and asserts the reader still works, so the constraint is enforced rather than merely documented.
