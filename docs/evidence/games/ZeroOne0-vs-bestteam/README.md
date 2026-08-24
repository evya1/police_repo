# ZeroOne0 vs bestteam — preserved match evidence

This directory preserves the real six-sub-game series identified by
`a42b2bb2-2312-c679-5e69-fa3d5ea0aad9`. The repository records the team's current designation
of the series as **counted**, while retaining the historical fact that the pre-game terms and
runner summary called it a warm-up. The designation is therefore auditable rather than a silent
rewrite.

## Result

- Game ID: `ZeroOne0-vs-bestteam`
- Sub-games: 6
- Group score: `ZeroOne0` 35, `bestteam` 75
- Sub-games won: `ZeroOne0` 1, `bestteam` 5
- Mutual game audits: passed in all six sub-games
- Replay: 6 verified, 0 tampered; 309 sealed records checked
- Current designation: counted by post-game team instruction

Police-versus-Thief role totals in the runner summary are 60–50. Those are not the group totals:
the two groups alternated roles, so the submission projection correctly derives the 35–75 group
score above.

## Files

- `kit-reference-v3/`: the required flat 14-file shape—one declaration, six configs, six logs,
  and one result. It passes the pinned kit's artifact checker and clean replay verifier. Its
  schema profile is `league-kit-reference-v3`, not an official-course-schema claim.
- `internal-replay/<game_uid>/`: the immutable 15-file internal bundle, including its SHA-256
  manifest.
- `source-result_warmup.json`: the original runner summary, preserved byte-for-byte.
- `user-designated-result_counted.json`: the later team-designated counted summary.
- `provenance.json`: hashes, commit evidence, verification coverage, and unresolved report data.
- `config/matches/ZeroOne0-vs-bestteam-20260824.json`: the unique agreed match configuration at
  repository root.

## Verification

From this repository:

```sh
uv run python scripts/replay.py \
  docs/evidence/games/ZeroOne0-vs-bestteam/internal-replay/a42b2bb2-2312-c679-5e69-fa3d5ea0aad9 \
  --json
```

Against the pinned `copthief-league-protocol` checkout:

```sh
python tools/check_artifacts.py <repo>/docs/evidence/games/ZeroOne0-vs-bestteam/kit-reference-v3
uv run python -m sparring.cli replay \
  <repo>/docs/evidence/games/ZeroOne0-vs-bestteam/kit-reference-v3 --expect-clean
```

## Submission status

The technical evidence is complete and replayable, but three historical reporting facts remain
explicit:

1. The pre-game correspondence declared the run uncounted; the counted designation was made
   after the completed game.
2. The preserved result-consensus block is `confirmed: false`; opponent confirmation of the
   post-game designation is not evidenced here.
3. Token usage for sub-game 5 and the final series total are unknown. Known ZeroOne0 usage is a
   lower bound of 4,613 tokens; no value is invented for the missing usage.

The evidence package does not claim that an instructor report email was sent. If the opponent
confirms the reclassification, both teams must independently send matching result JSON and the
missing token accounting must be resolved before this package can demonstrate every counted-game
reporting requirement.
