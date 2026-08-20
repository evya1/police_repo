# Internal Reporting Artifact Contract (NOT OFFICIAL)

This is a project-owned INTERNAL contract authorized by OPEN-001 operational convention. Official templates (INPUT-001) are still required and will replace this schema at the SAME boundary (schemas.py + this README) without changing builders/validators/signing seam.

## Artifacts

### Declaration
- Fields: game_uid, schema_version, team, role, members, police_repo_url, thief_repo_url, mcp_addresses, hardware, model, token_budget, start_time, end_time, num_games
- Canonical serialization: OPEN-007
- Signing seam: injected callable, no default
- Schema version: internal-1
- Immutability: finalized log is immutable

### SubGameConfig
- Fields: game_uid, game_id, schema_version, sub_game_index, role_for_this_sub_game, agreed_terms, git_commit
- Canonical serialization: OPEN-007
- Signing seam: injected callable, no default
- Schema version: internal-1
- Immutability: finalized log is immutable

### SubGameLog
- Fields: game_uid, game_id, schema_version, steps, finalized, signature
- Canonical serialization: OPEN-007
- Signing seam: injected callable, no default
- Schema version: internal-1
- Immutability: finalized log is immutable

### SeriesResult
- Fields: game_uid, schema_version, sub_game_results, total_police_score, total_thief_score, tie_applied, repo_links, total_llm_tokens_per_series
- Canonical serialization: OPEN-007
- Signing seam: injected callable, no default
- Schema version: internal-1
- Immutability: finalized log is immutable

## Label
INTERNAL CONTRACT — NOT OFFICIAL TEMPLATE CONFORMANCE

## Filenames (internal, deterministic)
`artifact_filename(artifact)` derives a replayable internal filename of the form
`{kind}_{game_uid}_{game_id|series}.json`. The four official REPORT-006 filenames are
binding but gated on INPUT-001; this internal derivation is replaced at the same
boundary when the official filenames arrive.

## Secret handling
No private secrets are accepted anywhere in an artifact. `validate_schema` recursively
rejects any secret-bearing key (password, secret, token, credential, api_key,
private_key, access_key, refresh_token, client_secret) including keys nested inside
open dict fields such as `agreed_terms` or inside `sub_game_results` entries.
