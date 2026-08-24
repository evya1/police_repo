---
artifact: contract
id: CT-07
status: draft
owner_component: C06 (Reporting & League)
shared: true
updated: 2026-08-24
---

# CT-07 — Kit Artifact Bundle

## Owner

C06 (Reporting & League). The pure builders live in the shared transport layer
(`common/transport/kit_names.py`, `kit_documents.py`, `kit_records.py`, `kit_settlement.py`,
`kit_consensus.py`) so both role repositories emit byte-identical structure.

## Consumers

The league kit's `tools/check_artifacts.py` and `sparring.cli replay`; the opponent's
cross-team join; the lecturer's grading tooling; and our own reporting path, which mails the
result artifact's canonical bytes.

## Input

One settled `SeriesResult` — its ledger rows and its per-sub-game `SubgameReplayEvidence`,
each already carrying sealed records, the negotiated terms as sealed bytes, and the live
audit's opponent-commitment ledger.

## Output

One flat directory, `<artifacts>/kit/<game_uid>/`, holding exactly 14 files:

| Count | Name | Content |
|---|---|---|
| 1 | `declaration_<game_id>.json` | identity, members, repos, endpoints, hardware, model, token cap, commit |
| 6 | `config_<game_id>_g<NN>.json` | the flat 14-key negotiated terms inline, plus `config_sha256` |
| 6 | `log_<game_id>_g<NN>.json` | `summary` plus every sealed record in the kit's nested envelope |
| 1 | `result_<game_id>.json` | per-sub-game rows, the derived aggregate, and `mutual_agreement` |

## Externally visible invariants

- All 14 files carry **one** `game_uid`, derived from the flat 14-key terms and the sorted
  group-id pair — never from a wider configuration object.
- `game_id` is the **sorted** pair joined by `-vs-`; a peer never names itself first.
- Records are `{"payload": ..., "nonce": ..., "commit": ...}`. The payload is byte-for-byte
  what was committed; nothing on this path re-hashes it.
- Every aggregate in `final_result` is **derived** from the rows, never declared beside them.
- The series tie award is **additive** at series level and published as `tie_score_each`. The
  diversity reward never enters `total_score`.
- A zeroed sub-game is credited to nobody: `tie: false`, `winner_group: null`.
- An opponent game count we cannot observe is `null` (unclaimed), never `0`.
- The `league` posture block is never defaulted; a warm-up never arms the league fields.
- Every document declares `schema_profile: "league-kit-reference-v3"` and claims nothing
  official (INPUT-001 remains open).

## Verification

```bash
python tools/check_artifacts.py <bundle> [--terms <flat terms>.json]   # ALL ARTIFACT CHECKS PASS
python -m sparring.cli replay   <bundle> --expect-clean                # 6 verified, 0 tampered
python tools/check_artifacts.py <ours> <theirs>                        # ALL SETS AGREE
```

The consensus digest is pinned by a third-party golden vector in
`tests/contract/kit_artifacts/test_kit_consensus.py`; see `tests/fixtures/kit_reference/`.
