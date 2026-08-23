# Replay CLI evidence transcripts (T047)

Sanitized `scripts/replay.py` transcripts against synthetic, deterministic six-sub-game
bundles built from `tests/unit/transport/replay_fixtures.py`'s fixed `GAME_ID`/`GAME_UID`
(`A-vs-B` / `a1b2c3d4-e5f6-7890-abcd-ef1234567890`). No secrets, private identifiers, or
credentials — every path shown is a placeholder, not a machine-local absolute path.

| File | Scenario | Verdict | Exit |
| --- | --- | --- | --- |
| `honest_human.txt` | honest bundle, human-readable output | `VERIFIED_OK` | 0 |
| `honest.json` | the same honest bundle, `--json` | `VERIFIED_OK` | 0 |
| `tampered.json.txt` | one sub-game's `move` field mutated, stale commit left in place | `TAMPERED` | 6 |
| `unanchored_recomputed.json.txt` | payload, nonce, commit, and manifest digest all rewritten consistently for a benign field | `VERIFIED_OK` | 0 |

## The unanchored-recomputed case (ADR-008)

`unanchored_recomputed.json.txt` is internally self-consistent — its verdict is
`VERIFIED_OK` — because a party able to rewrite payload, nonce, commit, and manifest digest
together can always make a local bundle internally consistent. `coverage.bundle_digests` is
`true` (this service validated the manifest, and it matches), but
`coverage.external_authenticity` stays `false`: no peer receipt or T018-authorized signature
was checked. Nothing in the human or JSON output describes this bundle as authentic — only
as unanchored and internally consistent, which is exactly what was verified.
