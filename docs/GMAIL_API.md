# Gmail reporting and runtime safety

This page documents the production reporting path for the Police peer. The governing source is
the official Police/Thief project book v3.0.0; the local extracted reporting pages are a
convenience copy only.

## Artifact inventory

The official names describe four artifact **families**, not four physical files. A six-sub-game
series publishes 14 JSON files:

1. one `declaration_<game_id>.json`;
2. six `config_<game_id>_g<NN>.json` files (`g01` through `g06`);
3. six `log_<game_id>_g<NN>.json` files; and
4. one `result_<game_id>.json`.

Every member carries the same series `game_id` and `game_uid`. Config/log pairs carry matching
sub-game numbers. Repository URLs, the exact playing commits, token evidence, timestamps, and the
mutual result agreement are validated before a counted report can proceed.

The binding Gmail report is the settled result JSON. Its canonical compact bytes are placed in
the text body and attached once under `result_<game_id>.json`. The other 13 artifacts are
published in the repository-backed kit bundle and are reachable through the result evidence.
Each team sends its own report only after both peers agree.

## Production path

```text
counted runner
  -> mutual log audit and result agreement
  -> 14-file kit publication and self-verification
  -> GmailKitReporter
  -> GmailSender.send_kit_result
  -> ExternalApiGatekeeper (reporting lane)
  -> users.messages.send
```

The Gatekeeper owns rate limiting, bounded concurrency/queueing, daily quota, denial-of-service
lockout, and HTTP 429 backoff. No reporting helper is allowed to construct a Google client or call
Gmail around this boundary.

## Recipient and authorization

The official counted-report destination is
`rmisegal+uoh26finalgame@gmail.com`. Delivery is still safe by default:

- `[email].mode = "dry-run"` composes a local outbox message and never contacts Gmail.
- `[email].mode = "off"` disables reporting composition.
- `[email].mode = "send"` is considered only in exact `counted` mode.
- Live delivery additionally requires the human-controlled `--authorize-email-send` flag.
- Unsettled, unaudited, inconsistent, malformed, or mutually unconfirmed results never reach
  Gmail.

The standalone `scripts/send_kit_email.py` command is dry-run-only. It reads its preview
recipient from `GMAIL_TEST_RECIPIENT`, writes a local MIME preview, and has no Google client or
live-send branch. Test recipient values are local secrets and must not be committed.

## OAuth secret files

The production adapter reuses the existing configuration seam:

```text
GMAIL_OAUTH_CLIENT_FILE=/absolute/local/path/to/credentials.json
GMAIL_OAUTH_TOKEN_FILE=/absolute/local/path/to/token.json
GMAIL_SENDER_EMAIL=<authenticated-sender-address>
```

The application does not auto-load an env file. Export these only in the explicitly authorized
counted execution shell. OAuth files stay outside Git with owner-only permissions. The stored
token metadata must declare exactly:

```text
https://www.googleapis.com/auth/gmail.send
```

A broader, missing, or malformed stored scope is rejected before Google credentials are loaded.
A valid refreshable token is reused. If no usable token exists, the installed-app browser consent
flow is the only supported way to create one; the token is atomically persisted with mode
`0600`.

Both repositories ignore `.env`, `.env.*` except the placeholder example, exact and variant
credential/token JSON filenames, and private-key formats. Repository quality checks also reject
those names if force-tracked.

## Tests and offline preview

Ordinary tests inject fake Gmail services and fake external providers. They do not read personal
OAuth/OpenRouter credentials and cannot send email.

An offline preview requires a local recipient environment variable but no Gmail credential:

```sh
GMAIL_TEST_RECIPIENT=<local-test-address> \
uv run python scripts/send_kit_email.py \
  artifacts/kit/<game_uid>/result_<game_id>.json \
  --artifact-root artifacts \
  --shared-config config/game.json
```

The command writes `outbox/<game_uid>/message.eml` plus a sanitized receipt. Do not publish that
private outbox.

## Relevant implementation

- `src/police_peer/wire/runtime_services.py`: one shared external-service Gatekeeper.
- `src/police_peer/wire/gmail_composition.py`: counted/dry-run composition and result validation.
- `src/police_peer/infra/gmail_oauth.py`: exact-scope OAuth loading and protected token writes.
- `src/police_peer/reporting/gmail.py`: MIME construction, Gmail send adapter, and idempotency.
- `src/police_peer/reporting/kit_bundle.py`: the 14-file projection.
- `tests/integration/test_gmail_production_composition.py`: fake-only production wiring tests.
