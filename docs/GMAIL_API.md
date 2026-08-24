# Gmail and email reporting API

This page documents the code on this branch, not a live-send procedure. The implemented Gmail
adapter can send an in-memory `internal-1` bundle, but the production CLI/runner never constructs
or calls it. The runner only writes replay and league-kit projections. Consequently,
`--mode counted` does **not** send email, `[email].mode = "dry-run"` does not create an outbox, and no live
authorization flag is implemented.

## Implemented path and components

The callable email path is:

```text
reporting.schemas objects
  -> ReportingArtifactBundle.validate_bundle()/to_attachments()
  -> ReportingPipeline.process_and_send()
  -> GmailSender.send_report()
  -> build_email_message() -> EmailMessage.as_bytes() -> URL-safe base64
  -> ExternalApiGatekeeper.execute(lane="reporting")
  -> users().messages().send(userId="me", body={"raw": ...}).execute()
  -> unchanged Gmail response dict -> two sent-UID JSON stores
```

This path does not start from `common.transport.series.SeriesResult`, does not read the files
published by `runner.py`, and has no production caller.

| Source and symbol | Contract, side effects, failures, caller/downstream |
| --- | --- |
| `src/police_peer/reporting/gmail.py::IdempotencyStore` | Runtime-checkable protocol. `is_sent(game_uid: str) -> bool`; `mark_sent(game_uid: str) -> None`. Implementations own persistence. Used by `GmailSender`; no downstream service. |
| `gmail.py::FileIdempotencyStore(file_path: str | Path = ".sent_game_uids.json")` | Reloads a JSON list for each `is_sent`; `mark_sent` writes a sorted, indented list through `<path>.tmp`, creates parents, then replaces the target. Missing, malformed, unreadable, or non-list input is treated as empty. Other write errors propagate. No locking; concurrent writers can lose updates. |
| `gmail.py::validate_oauth_scope(scopes: list[str] | str | None) -> None` | Accepts a non-empty value containing only the full send scope or literal `gmail.send`, after stripping each item. Raises `InvalidScopeError` for missing, empty, read/modify/compose, or any other scope. It validates caller input only; it neither loads nor inspects granted credentials. |
| `gmail.py::build_email_message(*, sender: str, recipient: str, subject: str, body: str, attachments: list[tuple[str, bytes]]) -> tuple[EmailMessage, str]` | Builds the MIME object and returns it plus ASCII URL-safe base64 of all MIME bytes. No I/O. Raises `AttachmentMissingError` for zero attachments or an empty member. It does not parse JSON, validate filenames/addresses, or restrict recipients. Called by `GmailSender`; downstream is Python's `email` package. |
| `gmail.py::GmailSender(...)` | Constructor requires an `ExternalApiGatekeeper` and a valid scope; accepts `sender_email: str = "peer@local"`, `default_recipient: str | None`, injected `service_client: Any`, and optional store. With no store it creates the working-directory store above. It does not construct an OAuth/Gmail client. |
| `gmail.py::GmailSender.send_report(*, game_uid: str, artifacts: list[tuple[str, bytes]], recipient: str | None = None, subject: str | None = None, body: str = "Automated Police/Thief series report attached.") -> dict[str, Any]` | Rejects an already-marked UID, missing client, or missing recipient; constructs the message; calls Gmail only through the Gatekeeper; marks sent only after the call returns; returns the client's dictionary unchanged (no required keys are validated or consumed). Client/Gatekeeper/store errors propagate. Called only by `ReportingPipeline` and tests. |
| `gmail.py::GmailSender.send_kit_result(*, game_uid: str, result: dict[str, Any], filename: str | None = None, recipient: str | None = None, subject: str | None = None) -> dict[str, Any]` | Kit-compatible send (SPEC §6.1, WARNINGS §6): body is the canonical compact bytes of `result`, the single attachment is that same file named `result_<game_id>.json` (or `filename`). Declaration/config/log are never emailed. Same guards (idempotency, client, recipient, draft) as `send_report`; the older 14-attachment path is untouched. |
| `gmail.py::GmailError` hierarchy | `GmailClientNotConfiguredError`, `InvalidScopeError`, `AttachmentMissingError`, `DraftSubstitutionError`, and `DuplicateSendError`. Missing recipient is instead `ValueError`. A missing/unusable `messages()` resource is treated as forbidden draft substitution. |
| `src/police_peer/reporting/artifacts.py::ReportingArtifactBundle` | Dataclass containing `Declaration`, six `SubGameConfig`, six `SubGameLog`, one `SeriesResult`, and optional `Callable[[bytes, str], bool]` verifier. `validate_bundle() -> None` validates counts, schemas, identifiers, finalization, and—only when a verifier exists—log signatures. `to_attachments() -> list[tuple[str, bytes]]` validates again and returns 14 ordered canonical JSON members. Pure; `ArtifactError` subclasses report malformed/inconsistent data. Used by `ReportingPipeline`. |
| `src/police_peer/reporting/pipeline.py::SentReportsStore(path: Path | None = None)` | Loads `.sent_reports.json` once into a cache. `is_sent(str) -> bool`; `mark_sent(str) -> None` overwrites compact sorted JSON. Missing/JSON/type errors load empty; other reads and all writes propagate. It creates no parent and has no atomic replace or locking. |
| `pipeline.py::settle_series(our_result, their_result) -> SeriesResult | None` | Returns `our_result` only when both total scores and `tie_applied` match. It checks no IDs, rows, signatures, repositories, or tokens. Pure and unused by the production runner. |
| `pipeline.py::KitInteropAdapter.to_kit_filename(artifact: Any) -> str` | Returns `<kind>_<game_uid>_<game_id-or-series>.json`; no validation or I/O. It is not called by the pipeline or runner and does not convert JSON shape. |
| `pipeline.py::ReportingPipeline(gmail_sender, sent_reports_store=None)` | Holds the sender and a second idempotency store. `process_and_send(bundle, *, agreement: AgreementOutcome, counted: bool = True, recipient: str | None = None, subject: str | None = None) -> dict[str, Any]` gates counted reports on `assert_reportable`, rejects a pipeline duplicate, validates/serializes, calls `GmailSender`, records the UID, and returns the unchanged client dict. `ArtifactError` and all sender errors become `ReportingPipelineError`; `NotAgreedError` and a final pipeline-store write error propagate directly. |
| `src/police_peer/infra/external_api_gatekeeper.py::ExternalApiGatekeeper.execute(...) -> Any` | Default lane is `reporting`. Enforces token bucket, DoS window/lockout, daily quota, concurrency, reserved reporting capacity, bounded queue, optional absolute deadline, and retries only errors classified as 429/rate-limit. Default backoffs are 0.5, 1, and 2 seconds (at most four total attempts). Returns the call result unchanged; otherwise raises a typed `GatekeeperError`. `GmailSender` supplies no deadline. |
| `src/police_peer/wire/identity_config.py::EmailSettings` / `load_email_settings(toml_data: dict) -> EmailSettings` | Frozen values `recipient: str` and `mode: str`, defaulting to the lecturer address and `dry-run`. Reads `[email]`, tolerates a missing/non-dict block, performs no value validation, and has no I/O. Loaded into `PrivateConfig`, but no sender or runner consumes it. |

## Configuration, recipient, and secrets

The only private-TOML email fields are `[email].recipient` and `[email].mode`. The loader accepts
arbitrary strings; the example uses `dry-run`, but there is no mode enum, send branch, outbox, or
explicit authorization parameter. `GmailSender` separately exposes `sender_email`,
`default_recipient`, `scopes`, `service_client`, and `idempotency_store` as constructor inputs.

- Authoritative recipient: `rmisegal+uoh26finalgame@gmail.com` (PDF p. 71, §9.3; p. 141,
  Appendix F table 20). `EmailSettings` defaults to it. **The Gmail adapter does not enforce it**:
  any non-empty per-call or default address is accepted, and a per-call value overrides the
  default.
- OAuth scope: `https://www.googleapis.com/auth/gmail.send` (PDF p. 105, Appendix A §1.3).
  `validate_oauth_scope` also accepts the shorthand `gmail.send`; broader scopes fail before a
  call.
- `.env.example` names `GMAIL_OAUTH_CLIENT_FILE`, `GMAIL_OAUTH_TOKEN_FILE`, and
  `REPORT_RECIPIENT`, but no application code reads them. `.env` is not automatically loaded.
- The PDF names local `credentials.json` and `token.json` (pp. 105–109, Appendix A). This
  repository ignores them but has no credential loader, refresh/consent flow, Gmail service
  builder, or required credential-file path. A caller must inject an already-built service.
- Neither `[email].mode` nor the comments about a human authorization flag are wired. Calling
  `send_report` or `process_and_send` with a real injected service is the authorization boundary
  in current code and immediately attempts transmission.

Passwords, OAuth client secrets, access/refresh tokens, credential JSON, authorization headers,
cookies/session data, and provider response identifiers must never enter Git, logs, artifacts,
message bodies, filenames, or exception text. `.gitignore`/repository safety checks cover local
credential filenames, and `validate_schema` recursively rejects secret-bearing **keys** in the
internal artifacts. It cannot recognize a secret hidden under an innocent key. Also, the
Gatekeeper and pipeline interpolate `str(client_exception)`, so the injected client must redact
sensitive response/header content before raising.

## Exact mail format

`GmailSender.send_report` generates:

- `From`: `sender_email`, default `peer@local`. It is only a MIME header; the API call authenticates
  as `userId="me"`, and the adapter does not reconcile the header with that account.
- `To`: per-call `recipient`, else `default_recipient`.
- `Subject`: per-call value, else `[PoliceThief-Report] Series <game_uid>`.
- Body: the exact default sentence shown in the signature above, encoded by `EmailMessage` as a
  `text/plain` body with its selected charset/transfer encoding.
- MIME: `multipart/mixed`; the text part comes first, followed by every attachment in the supplied
  list. Each attachment is `application/json`, uses the supplied filename, and is normally MIME
  base64-transfer-encoded by `EmailMessage`.
- Gmail request: `{"raw": <urlsafe-base64 of message.as_bytes()>}` passed to
  `users().messages().send(userId="me", ...).execute()`. Python's URL-safe encoder retains `=`
  padding. No draft endpoint is allowed.
- Response: whatever dictionary `.execute()` returns. The code reads no response field and does
  not persist the response.

Sanitized structure (angle-bracketed terms are runtime values, not example data):

```text
From: <sender_email>
To: <recipient>
Subject: [PoliceThief-Report] Series <game_uid>
MIME-Version: 1.0
Content-Type: multipart/mixed; boundary=<generated-boundary>

--<generated-boundary>
Content-Type: text/plain; charset="utf-8"

Automated Police/Thief series report attached.
--<generated-boundary>
Content-Type: application/json
Content-Disposition: attachment; filename="<artifact_filename>"
Content-Transfer-Encoding: base64

<base64 of the exact bytes returned by reporting.schemas.serialize>
--<generated-boundary>--
```

MIME boundaries and header folding are chosen by the standard library, so the complete encoded
`raw` string is not deterministic even when attachment JSON bytes are.

### `send_kit_result` — kit-compatible format

`GmailSender.send_kit_result` is the league-kit-compatible sender (SPEC §6.1, WARNINGS §6). It
emails the **result only**:

- Body: the **canonical compact** bytes of the kit result (`common.transport.canonical.canonical_bytes`, `sort_keys=True, ensure_ascii=False, separators=(",", ":")`) — never a pretty-printed re-serialization. `EmailMessage` appends a trailing newline to the `text/plain` body, which is accepted.
- Attachment: exactly **one** named file, `result_<game_id>.json` (or the supplied `filename`), whose payload is the same canonical bytes.
- Declaration/config/log artifacts are **never** emailed; they are published in the repos and reached via the result's `links.github` (rule 49).

## JSON attachments and source map

The pipeline attaches exactly 14 `internal-1` objects in deterministic **category** order:

1. `declaration_<game_uid>_series.json`;
2. six `sub_game_config_<game_uid>_<game_id>.json` members in the bundle list's order;
3. six `log_<game_uid>_<game_id>.json` members in the bundle list's order;
4. `result_<game_uid>_series.json`.

The lists are not sorted, so ordering within configs/logs is caller-determined. Bytes come from
`common.transport.canonical.canonical_bytes`: UTF-8, keys sorted, compact `,`/`:` separators, and
Unicode unescaped. Filenames are deterministic but are the internal convention, not Appendix F's
`declaration_<game_id>.json`, `config_<game_id>_g<NN>.json`,
`log_<game_id>_g<NN>.json`, and `result_<game_id>.json` grammar.

| Output | Defining symbol | Producer | Validator | Email attachment builder |
| --- | --- | --- | --- | --- |
| Internal declaration | `reporting.schemas.Declaration` / `artifact_filename` | `build_declaration`; no code writes this email object to disk | `validate_schema`, `validate_identifiers` | `ReportingArtifactBundle.to_attachments` |
| Six internal configs | `SubGameConfig` / `artifact_filename` | `build_sub_game_config`; no email-path disk producer | same, per config/log pair | `ReportingArtifactBundle.to_attachments` |
| Six internal logs | `SubGameLog` / `artifact_filename` | `build_sub_game_log`, `finalize_log`; no email-path disk producer | schema/IDs/finalized; optional `verify_artifact` | `ReportingArtifactBundle.to_attachments` |
| Internal series result | `reporting.schemas.SeriesResult` / `artifact_filename` | `build_series_result`; no email-path disk producer | schema and series UID | `ReportingArtifactBundle.to_attachments` |
| On-disk league-kit declaration/config/log/result | `common.transport.kit_documents.build_*` and `kit_names.*_name` | `reporting.kit_bundle.build_kit_bundle` / `publish_kit_bundle`, called by `settlement.publish_kit` | post-write `_self_verify` reproduces log commitments; builders validate selected structure | **none** |

The emailed bytes are therefore not bytes read from disk and are not identical to the on-disk
league-kit files. Kit files are a different `league-kit-reference-v3` schema and are pretty JSON
with a trailing newline; email attachments are compact `internal-1` JSON built from different
dataclasses. The Gmail path sends all 14 internal objects, while PDF p. 79, §9.3.3 identifies the
final result artifact as the binding emailed report. It does **not** send the exact league-kit
JSON shape required by the PDF. The mismatch is at
`reporting/artifacts.py::ReportingArtifactBundle.to_attachments`. The separate
`reporting/kit_bundle.py::build_kit_bundle` projection uses Appendix F filenames but labels itself
`league-kit-reference-v3`, not official template conformance, and has no email consumer.

A missing config/log count, mismatched UID/ID, wrong field type, secret-bearing key, or unfinalized
log stops before Gmail with `ReportingPipelineError` caused by an `ArtifactError`. With a bundle
`verifier`, missing/invalid log signatures also stop. With `verifier=None` (the default), finalized
logs are accepted without cryptographic re-verification. `build_email_message` independently
rejects an empty attachment list/member but does not reject malformed JSON.

## Results, persistence, and failure behavior

No `SendIntent`, `SendReceipt`, outbox model, or Gmail response model is implemented.

| Situation | Exact current result and state |
| --- | --- |
| Dry run | No pipeline mode exists. `build_email_message` can compose in memory and return `(EmailMessage, raw_base64)` without I/O; nothing is persisted unless the caller does so. `[email].mode` has no effect. |
| Successful send | Gmail's unvalidated response dict is returned. `GmailSender` adds the UID to `.sent_game_uids.json`; then `ReportingPipeline` adds it to `.sent_reports.json`. Neither stores a response/receipt. |
| Duplicate | Pipeline-store hit raises `ReportingPipelineError` before serialization. Sender-store hit raises `DuplicateSendError`; through the pipeline it is wrapped as `ReportingPipelineError`. No Gmail call occurs. |
| Gmail rejection or authentication failure | Client exception becomes `ExternalCallError` (after eligible 429 retries) and then `ReportingPipelineError`; neither sent store is updated. |
| Timeout | The adapter configures no client timeout and passes no Gatekeeper deadline. A client-raised timeout is ordinarily wrapped as above. Gatekeeper `DeadlineExceededError` is possible only for a direct caller that supplies a deadline to `execute`, not through `GmailSender`. |
| Ambiguous outcome | A remote acceptance followed by a client exception is unmarked and may be retried/re-sent; there is no provider-id reconciliation. If Gmail returns but a sender-store write fails, the exception propagates and the message may exist without durable state. If only the later pipeline-store write fails, sender state exists but the pipeline reports failure. |
| Invalid OAuth scope | `InvalidScopeError` at `GmailSender` construction; no client/Gmail call. |
| Unauthorized recipient | No authorization check exists. Any non-empty address is accepted; only absence raises `ValueError`. |
| Missing Gmail client | `GmailClientNotConfiguredError` before message construction/Gatekeeper. |
| Missing/invalid artifacts | Count/schema/identifier/finalization/optional-signature failures are wrapped as `ReportingPipelineError`; zero/empty raw members raise `AttachmentMissingError`, wrapped by the pipeline. |
| Gatekeeper refusal | Rate bucket, DoS, quota, queue, or deadline errors become `ReportingPipelineError`; no sent state. Non-429 client failures are not retried. |

Both sent files are relative to the process working directory unless explicit paths are injected.
They are UID lists, not receipts. The two-store update is not transactional.

## Friendly, counted, and production behavior

- Warm-up/friendly: `runner.run_one_peer(mode="warmup")` plays and settles; with
  `artifacts_dir`, it writes a summary and, for settled results, replay and optional league-kit
  directories. It never emails. A direct test-only `process_and_send(..., counted=False)` actually
  sends through its injected client even without agreement; `counted=False` is an agreement-gate
  bypass, not a dry run.
- Counted/league: readiness and mutual agreement are enforced. With `artifacts_dir`, the same disk
  outputs are written, with counted metadata in the kit. Unagreed counted play exits 6. Agreed
  counted play can exit 0, but still never emails.
- Dry-run reporting: not wired. The parsed TOML setting produces no MIME or file.
- Explicitly authorized live send: not wired. There is no CLI option or production composition
  root for a Gmail client/pipeline; only direct API callers can inject a real service and call it.

Production entry points are `police_peer.cli.main -> runner.run_one_peer`. `runner.py` imports
replay/settlement/kit functions, but imports neither `GmailSender` nor `ReportingPipeline`. Selecting
`counted`, `competition`, or `live` does not imply email (only exact `counted` triggers counted
readiness/metadata checks).

## Offline usage examples

These examples use an injected fake and cannot contact Gmail. Assume `bundle` is a
`ReportingArtifactBundle` made with the builders in `reporting.schemas`, as in
`tests/integration/test_reporting_pipeline.py`.

```python
from pathlib import Path

from common.transport.kit_agreement import AgreementOutcome
from police_peer.infra.external_api_gatekeeper import ExternalApiGatekeeper
from police_peer.reporting.gmail import FileIdempotencyStore, GmailSender
from police_peer.reporting.pipeline import ReportingPipeline, SentReportsStore

class FakeMessages:
    def send(self, userId: str, body: dict):  # noqa: N803
        self.request = (userId, body)
        return self
    def execute(self) -> dict:
        return {}

class FakeService:
    def __init__(self) -> None:
        self.resource = FakeMessages()
    def users(self):
        return self
    def messages(self):
        return self.resource

fake = FakeService()
sender = GmailSender(
    gatekeeper=ExternalApiGatekeeper(),
    scopes=["https://www.googleapis.com/auth/gmail.send"],
    default_recipient="rmisegal+uoh26finalgame@gmail.com",
    service_client=fake,
    idempotency_store=FileIdempotencyStore(Path("artifacts/state/gmail-sent.json")),
)
pipeline = ReportingPipeline(sender, SentReportsStore(Path("artifacts/state/pipeline-sent.json")))
agreement = AgreementOutcome(True, "<agreement reason supplied by settlement>")
receipt = pipeline.process_and_send(bundle, agreement=agreement, counted=True)
assert receipt == {}                 # exactly the fake service's dict
assert fake.resource.request[0] == "me"
```

Compose a real bundle without any send or persistence:

```python
from police_peer.reporting.gmail import build_email_message

message, raw = build_email_message(
    sender="peer@local",
    recipient="rmisegal+uoh26finalgame@gmail.com",
    subject=f"[PoliceThief-Report] Series {bundle.declaration.game_uid}",
    body="Automated Police/Thief series report attached.",
    attachments=bundle.to_attachments(),
)
assert message.get_content_type() == "multipart/mixed"
assert isinstance(raw, str)
```

Authorization must currently be owned by the caller. This remains offline because the service is
the fake above:

```python
live_send_authorized = True  # application-owned; no equivalent pipeline argument exists
if live_send_authorized:
    fake_receipt = pipeline.process_and_send(bundle, agreement=agreement, counted=True)
```

The production runner's generated files, when `--artifacts-dir artifacts` is supplied, are under
`artifacts/result_<game_id>.json`, `artifacts/replay/<game_uid>/`, and
`artifacts/kit/<game_uid>/`. The example's two UID stores are under `artifacts/state/`. There is no
generated Gmail outbox or receipt file.

## PDF compliance

| PDF requirement | Implemented location | Status |
| --- | --- | --- |
| Each peer automatically emails after every legal counted game (p. 71, §9.3) | `reporting.pipeline.ReportingPipeline.process_and_send`; absent from `runner.run_one_peer` | not wired |
| Only `rmisegal+uoh26finalgame@gmail.com` is allowed (p. 71; p. 141, App. F table 20) | `wire.identity_config.LECTURER_REPORT_ADDRESS`; `GmailSender.send_report` accepts overrides | partial |
| Send-only OAuth scope (p. 105, App. A §1.3) | `reporting.gmail.GMAIL_SEND_SCOPE` / `validate_oauth_scope` | implemented |
| Local OAuth files and consent/refresh flow (pp. 105–109, App. A) | ignore/safety configuration; no Gmail client factory | missing |
| Gatekeeper rate, quota, DoS, and 429 backoff (pp. 72–79, §9.3.1–3) | `infra.external_api_gatekeeper.ExternalApiGatekeeper` | implemented |
| Machine-readable JSON attachment, not plaintext (pp. 78–79, §9.3.3) | `build_email_message`; `ReportingArtifactBundle.to_attachments` | partial |
| Appendix F filenames/common IDs and binding final-result JSON (pp. 78–79; p. 141) | kit: `common.transport.kit_names`; email: internal `reporting.schemas.artifact_filename` | partial |
| Both peers independently send consistent reports (p. 78, §9.3.3; App. E rule 35) | `kit_agreement.assert_reportable`; email pipeline is not production-reachable | not wired |
| Warm-ups do not count; one counted game per opponent (p. 70, §9.2.1; p. 133, App. E rule 52) | `league.readiness`, settlement/kit metadata, `runner.run_one_peer` | implemented |
| Dry-run plus explicitly authorized live send | TOML `EmailSettings.mode`; no consumer/authorization flag | not wired |
