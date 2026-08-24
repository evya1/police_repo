---
artifact: task
id: T056
title: Emit the league-kit 14-artifact bundle from a settled series
status: done
owner: orchestrator
component: C06
depends_on: [T046, T047, T053]
related_requirements: [REPORT-005, REPORT-006, OBS-006]
related_decisions: [ADR-012]
related_contracts: [CT-07]
write_set:
  - common/transport/kit_names.py
  - common/transport/kit_records.py
  - common/transport/kit_documents.py
  - common/transport/kit_settlement.py
  - common/transport/kit_consensus.py
  - common/transport/atomic_publish.py
  - src/police_peer/reporting/kit_bundle.py
---

# T056 — Kit bundle emission

## Goal

Project one settled series into the kit's four-artifact format so that, on a bundle produced by
the real composition path, both league gates pass.

## What was actually wrong

Reproduced against the pinned kit before any code was written:

| Gate | Before | Cause |
|---|---|---|
| `check_artifacts.py` | 16 failures | 6 naming causes: `sub_game_index` vs `sub_game_number`, no `groups`/`num_sub_games`, no log `summary`, no `final_result`, record-count rows instead of score rows |
| `sparring.cli replay` | `0 verified, 6 tampered` | one shape cause: flat records where the auditor reads `record["payload"]` |

The commitments were already correct — every internal record reproduces its commit under the
kit's own construction. See ADR-012.

## Approach

A pure projection. `league_kit_envelope.wrap_outbound_records` supplies the envelope;
`evidence.terms_bytes` supplies the sealed terms; `common/domain/scoring` supplies the fixed
score table. The atomic-publication sequence was extracted from `replay_bundle.py` into
`common/transport/atomic_publish.py` so both bundles share one implementation rather than two
that could drift.

## Acceptance

```
uv run python scripts/smoke_replay_integration.py --config config/game.json \
      --artifact-root /tmp/w1p3 --json
python tools/check_artifacts.py /tmp/w1p3/kit/<uid>            -> ALL ARTIFACT CHECKS PASS (0)
python -m sparring.cli replay   /tmp/w1p3/kit/<uid> --expect-clean -> 6 verified, 0 tampered (0)
uv run python scripts/replay.py /tmp/w1p3/replay/<uid>          -> verified_ok (0)
```

Recorded result: all four pass. The checker additionally reported
`game_uid DERIVES from the flat terms (the config artifact's own terms)` without needing
`--terms`, because the config artifact carries exactly the 14-key set inline.

## Notes

`schema_profile` is `league-kit-reference-v3`, never "official": INPUT-001 (the official
templates) is still MISSING, and no document may claim a compliance nobody has verified.
