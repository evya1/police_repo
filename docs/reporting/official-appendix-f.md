# Official Appendix-F reporting

The production boundary publishes exactly 14 JSON files at
`<artifacts>/official/<game_uid>/`: one declaration, configs `g01`–`g06`, logs `g01`–`g06`,
and one result. Run `uv run python scripts/validate_official_artifacts.py <directory>` before
using a result. Outward timestamps declare `Asia/Jerusalem`; sealed record timestamps remain
unchanged because they are part of commit/reveal evidence.

Artifact classification:

| Location or family | Classification | Meaning |
|---|---|---|
| runtime `official/<game_uid>/` after validator success | `OFFICIAL_VALID` | current schema 1.1 Appendix-F output |
| runtime `replay/<game_uid>/` and legacy `internal-1` objects | `INTERNAL_ONLY` | richer replay/audit or superseded email model |
| tracked `docs/evidence/**/kit-reference-v3` and historical generated results | `STALE_OR_INVALID` | retained evidence; never a current official example |
| `tests/fixtures/**` and test-built JSON | `TEST_FIXTURE` | owned fake data; no personal credentials |

For a deterministic two-peer warm-up, give both processes the same shared JSON with their
actual group IDs, complete private identity TOMLs, template LLM mode, and email mode `off`.
Start the Thief peer and Police peer with reciprocal local MCP URLs:

```bash
# Thief repository
uv run python -m thief_peer --listen-port 18102 \
  --peer-url http://127.0.0.1:18101/mcp --shared-config /tmp/warmup-game.json \
  --private-config /tmp/warmup-thief.toml --group-id warmup-thief \
  --mode warmup --artifacts-dir /tmp/warmup/thief --wire-profile internal

# Police repository
uv run python -m police_peer --listen-port 18101 \
  --peer-url http://127.0.0.1:18102/mcp --shared-config /tmp/warmup-game.json \
  --private-config /tmp/warmup-police.toml --group-id warmup-police \
  --mode warmup --artifacts-dir /tmp/warmup/police --wire-profile internal
```

Template mode consumes known zero LLM tokens. A real OpenRouter run first loads the protected
environment file and uses `deepseek/deepseek-v4-flash-0731:nitro`; omitting `provider_slug`
lets OpenRouter select the fastest healthy Nitro provider. Unknown usage fails counted
publication.

For counted play, replace local endpoints and fixture identities with mutually verified live
values, use `--mode counted --group-code-confirmed --public-url <actual-url>`, and configure
the OAuth paths through `GMAIL_OAUTH_CLIENT_FILE` and `GMAIL_OAUTH_TOKEN_FILE`. A live send
also requires `--authorize-email-send`; absence of that flag cannot contact Gmail. Dry-run
composition writes `.eml` outside the official directory and attaches the exact published
result bytes.
