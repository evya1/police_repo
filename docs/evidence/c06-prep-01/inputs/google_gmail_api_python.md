# Google Gmail API — Python send-only mechanics (fetched 2026-08-18)

Sources:
- https://developers.google.com/workspace/gmail/api/guides/sending
- https://developers.google.com/workspace/gmail/api/auth/scopes
- https://developers.google.com/workspace/gmail/api/quickstart/python

## Send-only OAuth scope (exact string)
```
https://www.googleapis.com/auth/gmail.send
```
Permits: "Send email on your behalf." Does NOT permit read, draft management, or
mailbox modification (distinct from `gmail.compose`, `gmail.modify`, `mail.google.com`).

## Send call
`users.messages.send` — Python: `service.users().messages().send(userId="me", body=create_message).execute()`

## Message construction
1. Build RFC 2822 MIME message, e.g. via `email.message.EmailMessage`.
2. Encode: `base64.urlsafe_b64encode(message.as_bytes()).decode()`
3. Request body: `{"raw": encoded_message}`
Multi-part MIME (attachments) supported via the same email-library + base64url path.

## Python client library
- Packages: `google-api-python-client`, `google-auth-httplib2`, `google-auth-oauthlib`
- Build client: `googleapiclient.discovery.build("gmail", "v1", credentials=creds)`

## Credential/token handling (installed-app flow)
- `credentials.json`: OAuth 2.0 Client ID JSON from Google Cloud Console, local file.
- `token.json`: written after first authorization; loaded on subsequent runs.
- Flow: `InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)`,
  `creds = flow.run_local_server(port=0)`.
- Refresh: if `not creds or not creds.valid` and a refresh token exists,
  `creds.refresh(Request())`; else re-run the consent flow. Persist via
  `token.json`.

## Idempotency
Google's own documentation does not define an idempotency key or duplicate-send
protection for `messages.send`. Any duplicate-send guard is an application-level
(project-owned) responsibility, not a Gmail API feature.
