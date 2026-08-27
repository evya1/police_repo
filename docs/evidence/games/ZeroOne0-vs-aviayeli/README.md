# ZeroOne0 vs aviayeli — submitted counted series

This directory preserves the evidence for the six-sub-game series selected by
ZeroOne0 for final league reporting. The Gmail API acknowledged exactly one
ZeroOne0 submission on 2026-08-27. No email envelope, address, OAuth material,
or provider message identifier is stored in the repository.

## Confirmed result

| Field | Value |
| --- | --- |
| Game ID | `ZeroOne0-vs-aviayeli` |
| Game UID | `ff90bd18-f873-981a-e1ca-0b89e6f9f03c` |
| Series | Six completed sub-games |
| Winner | `aviayeli` |
| Score | `ZeroOne0 40` — `aviayeli 60` |
| Sub-games won | `ZeroOne0 2` — `aviayeli 4` |
| ZeroOne0 play commit | `62404917a4c43acdc600c4b72adecbbe8d6df341` |
| aviayeli play commit | `b32ffb1cd752f623a72fcfe60c6717fc7e8d07b8` |
| Counted-night consensus SHA-256 | `c39d331ce8c45e30823baf2aeae58053020836542aa6e14d584fa2a58af23ee6` |
| Full post-game settlement SHA-256 | `5077306a3703467941ce7593bcf805a022c9f162588acc4f3feca97a045b0373` |

The counted-night digest covers the 1,224-byte historical consensus block and
uses the reference-v3 `cop`/`thief` vocabulary. The later 3,997-byte settlement
scope includes the complete Appendix-F rows. Both digests are retained with
their distinct scopes; neither value is rewritten or presented as the other.

## Official 14-file lifecycle bundle

The directory
[`official/ff90bd18-f873-981a-e1ca-0b89e6f9f03c/`](official/ff90bd18-f873-981a-e1ca-0b89e6f9f03c/)
contains exactly these 14 official JSON files:

1. [`declaration_ZeroOne0-vs-aviayeli.json`](official/ff90bd18-f873-981a-e1ca-0b89e6f9f03c/declaration_ZeroOne0-vs-aviayeli.json)
2. [`config_ZeroOne0-vs-aviayeli_g01.json`](official/ff90bd18-f873-981a-e1ca-0b89e6f9f03c/config_ZeroOne0-vs-aviayeli_g01.json)
3. [`config_ZeroOne0-vs-aviayeli_g02.json`](official/ff90bd18-f873-981a-e1ca-0b89e6f9f03c/config_ZeroOne0-vs-aviayeli_g02.json)
4. [`config_ZeroOne0-vs-aviayeli_g03.json`](official/ff90bd18-f873-981a-e1ca-0b89e6f9f03c/config_ZeroOne0-vs-aviayeli_g03.json)
5. [`config_ZeroOne0-vs-aviayeli_g04.json`](official/ff90bd18-f873-981a-e1ca-0b89e6f9f03c/config_ZeroOne0-vs-aviayeli_g04.json)
6. [`config_ZeroOne0-vs-aviayeli_g05.json`](official/ff90bd18-f873-981a-e1ca-0b89e6f9f03c/config_ZeroOne0-vs-aviayeli_g05.json)
7. [`config_ZeroOne0-vs-aviayeli_g06.json`](official/ff90bd18-f873-981a-e1ca-0b89e6f9f03c/config_ZeroOne0-vs-aviayeli_g06.json)
8. [`log_ZeroOne0-vs-aviayeli_g01.json`](official/ff90bd18-f873-981a-e1ca-0b89e6f9f03c/log_ZeroOne0-vs-aviayeli_g01.json)
9. [`log_ZeroOne0-vs-aviayeli_g02.json`](official/ff90bd18-f873-981a-e1ca-0b89e6f9f03c/log_ZeroOne0-vs-aviayeli_g02.json)
10. [`log_ZeroOne0-vs-aviayeli_g03.json`](official/ff90bd18-f873-981a-e1ca-0b89e6f9f03c/log_ZeroOne0-vs-aviayeli_g03.json)
11. [`log_ZeroOne0-vs-aviayeli_g04.json`](official/ff90bd18-f873-981a-e1ca-0b89e6f9f03c/log_ZeroOne0-vs-aviayeli_g04.json)
12. [`log_ZeroOne0-vs-aviayeli_g05.json`](official/ff90bd18-f873-981a-e1ca-0b89e6f9f03c/log_ZeroOne0-vs-aviayeli_g05.json)
13. [`log_ZeroOne0-vs-aviayeli_g06.json`](official/ff90bd18-f873-981a-e1ca-0b89e6f9f03c/log_ZeroOne0-vs-aviayeli_g06.json)
14. [`result_ZeroOne0-vs-aviayeli.json`](official/ff90bd18-f873-981a-e1ca-0b89e6f9f03c/result_ZeroOne0-vs-aviayeli.json)

The official result-file SHA-256 is
`1cbdb84429a9858f2f3de39dba01994f362768dcfb13d16b5caf285cb9a81d4a`.

Validate the reopened bundle from the repository root:

```sh
uv run python scripts/validate_official_artifacts.py \
  docs/evidence/games/ZeroOne0-vs-aviayeli/official/ff90bd18-f873-981a-e1ca-0b89e6f9f03c
```

## Exact submitted attachment

[`submission-email/result_ZeroOne0-vs-aviayeli.json`](submission-email/result_ZeroOne0-vs-aviayeli.json)
is the exact single JSON attachment acknowledged by Gmail. It uses the
counterparty-compatible reference-v3 reporting envelope, promotes the
counted-night digest, and preserves the full post-game digest in its
`official_settlement` block.

Its byte-level SHA-256 is
`bee87dd3744646cceae0327b5a7637eb9c083d522777a752873d27390990abfe`.
This copy is kept separate so the validated Appendix-F lifecycle bundle remains
unchanged and reproducible.
