# Gmail delivery (`gmail.py`)

This module constructs JSON-attachment email and sends it through a Gmail-compatible client behind `ExternalApiGatekeeper`. `GMAIL_SEND_SCOPE` is the full allowed scope, `https://www.googleapis.com/auth/gmail.send`.

## Errors and store protocol

`GmailError` is the base for `GmailClientNotConfiguredError`, `InvalidScopeError`, `AttachmentMissingError`, `DraftSubstitutionError`, and `DuplicateSendError`. Missing recipients raise `ValueError`, not `GmailError`. Gatekeeper, client, JSON, and filesystem exceptions can also propagate.

`IdempotencyStore` is a runtime-checkable protocol:

- `mark_sent(game_uid: str) -> None`
- `is_sent(game_uid: str) -> bool`

`FileIdempotencyStore(file_path: str | Path = ".sent_game_uids.json")` implements it as a JSON list of sorted UIDs. `is_sent` reloads on each call. A missing file, any read/parse error, or valid non-list JSON is treated as empty. `mark_sent` creates parent directories, writes indented JSON to `<suffix>.tmp`, then replaces the target; an existing target is overwritten, never appended. Concurrent writers are not coordinated.

## Functions

- `validate_oauth_scope(scopes: list[str] | str | None) -> None` accepts a non-empty string or list containing only `gmail.send` or `GMAIL_SEND_SCOPE`, after stripping whitespace. `None`, an empty list, or any other entry raises `InvalidScopeError`. It does not deduplicate scopes or contact OAuth services.
- `build_email_message(*, sender: str, recipient: str, subject: str, body: str, attachments: list[tuple[str, bytes]]) -> tuple[EmailMessage, str]` requires at least one attachment and non-empty bytes for every member. It returns the constructed message plus URL-safe base64 of its complete MIME bytes. Every attachment is labeled `application/json`; filenames and JSON syntax are not validated. No network or filesystem I/O occurs.

## `GmailSender`

Constructor:

```text
GmailSender(
    gatekeeper: ExternalApiGatekeeper,
    scopes: list[str] | str | None = None,
    sender_email: str = "peer@local",
    default_recipient: str | None = None,
    service_client: Any = None,
    idempotency_store: IdempotencyStore | None = None,
)
```

Construction validates scopes immediately. A missing store creates `FileIdempotencyStore()` in the working directory. The package does not build the Gmail client or read OAuth/environment configuration.

`send_report(*, game_uid: str, artifacts: list[tuple[str, bytes]], recipient: str | None = None, subject: str | None = None, body: str = "Automated Police/Thief series report attached.") -> dict[str, Any]`:

1. Rejects a previously sent UID with `DuplicateSendError`.
2. Requires a service client, then a per-call or default recipient.
3. Defaults subject to `[PoliceThief-Report] Series <game_uid>` and builds the MIME payload.
4. Through the Gatekeeper's default `reporting` lane, calls a client equivalent to `users().messages().send(userId="me", body={"raw": ...}).execute()`. A missing/unusable `messages` resource raises `DraftSubstitutionError`.
5. Marks the UID sent only after the Gatekeeper call returns, then returns the client's dictionary unchanged.

If the remote send succeeds but `mark_sent` fails, that filesystem/store exception propagates and the durable duplicate marker is absent.

## Minimal offline example

```python
from police_peer.reporting.gmail import build_email_message

message, encoded = build_email_message(
    sender="sender@example.invalid",
    recipient="recipient@example.invalid",
    subject="Series report",
    body="Attached.",
    attachments=[("result.json", b'{"status":"placeholder"}')],
)
assert message.get_content_type() == "multipart/mixed"
assert isinstance(encoded, str)
```
