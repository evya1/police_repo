# ZeroOne0 vs bestteam — counted match evidence

This directory contains the completed counted match `ZeroOne0-vs-bestteam`, played on 2026-08-24 from approximately 22:31 to 22:44.

## Confirmed result

| Field | Value |
| --- | --- |
| Game ID | `ZeroOne0-vs-bestteam` |
| Game UID | `a42b2bb2-2312-c679-5e69-fa3d5ea0aad9` |
| Mode | `counted` |
| Opponent | `bestteam` |
| Settled | `true` |
| Subgames | Six completed |
| ZeroOne0 roles | Police in 1, 3, 5; Thief in 2, 4, 6 |
| Audit | `audit_ok: true` in every subgame |
| Final score | ZeroOne0 35 — bestteam 75 |
| Replay | Six verified, zero tampered; 309 sealed records checked |

## Artifact map

| Evidence | Path |
| --- | --- |
| Canonical game artifact | [`game.json`](game.json) |
| Completed result | [`result_ZeroOne0-vs-bestteam.json`](kit-reference-v3/result_ZeroOne0-vs-bestteam.json) |
| Match declaration and repository identities | [`declaration_ZeroOne0-vs-bestteam.json`](kit-reference-v3/declaration_ZeroOne0-vs-bestteam.json) |
| Per-subgame configurations | [`kit-reference-v3/`](kit-reference-v3/) |
| Per-subgame logs, transcript, commitments, and audit rows | [`kit-reference-v3/`](kit-reference-v3/) |
| Immutable internal replay bundle | [`internal-replay/a42b2bb2-2312-c679-5e69-fa3d5ea0aad9/`](internal-replay/a42b2bb2-2312-c679-5e69-fa3d5ea0aad9/) |
| Replay manifest and digests | [`manifest_ZeroOne0-vs-bestteam.json`](internal-replay/a42b2bb2-2312-c679-5e69-fa3d5ea0aad9/manifest_ZeroOne0-vs-bestteam.json) |
| Audit and reporting provenance | [`provenance.json`](provenance.json) |
| Agreed match configuration | [`config/matches/ZeroOne0-vs-bestteam-20260824.json`](../../../../config/matches/ZeroOne0-vs-bestteam-20260824.json) |

The declaration, agreed configuration, result agreement record, logs, transcript records, commitment reveals, replay manifest, and reporting provenance form the complete submission evidence for the series.

## Verification

Verify the Replay GUI service against the completed kit bundle:

```sh
uv run python scripts/replay_gui.py \
  docs/evidence/games/ZeroOne0-vs-bestteam/kit-reference-v3 \
  --verify-only
```

Verify all six immutable replay subgames:

```sh
uv run python scripts/replay.py \
  docs/evidence/games/ZeroOne0-vs-bestteam/internal-replay/a42b2bb2-2312-c679-5e69-fa3d5ea0aad9 \
  --json
```

Expected result: `verified_ok`, six verified subgames, zero tampered subgames, and successful integrity, physics, outcome, and bundle-digest checks.
