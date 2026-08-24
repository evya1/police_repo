# Reporting pipeline (`pipeline.py`)

This module gates the older `internal-1` email path on agreement, reconciles a `ReportingArtifactBundle`, sends it through `GmailSender`, and records completion.

## Public API

`ReportingPipelineError` wraps bundle `ArtifactError` failures, duplicate processing, and transmission failures.

`SentReportsStore(path: Path | None = None)` defaults to `.sent_reports.json`. At construction it loads a JSON value into an in-memory `set`; missing files and `JSONDecodeError`/`TypeError` become empty. Other read errors propagate. `is_sent(game_uid: str) -> bool` checks the cache. `mark_sent(game_uid: str) -> None` adds the UID and overwrites the file with a compact sorted JSON list. It does not create parent directories, lock concurrent writers, or use a temporary file.

`settle_series(our_result: reporting.schemas.SeriesResult, their_result: reporting.schemas.SeriesResult) -> reporting.schemas.SeriesResult | None` returns `our_result` when and only when the two total scores and `tie_applied` values are equal; otherwise it returns `None`. Despite the descriptive docstring, it does not inspect UIDs, sub-game results, completeness, signatures, or repo/token fields.

`KitInteropAdapter` provides the static method `to_kit_filename(artifact: Any) -> str`, returning `<kind>_<game_uid>_<game_id-or-series>.json` with the same fallbacks as `artifact_filename`. It performs no validation or I/O.

`ReportingPipeline(gmail_sender: GmailSender, sent_reports_store: SentReportsStore | None = None)` retains both dependencies; omitting the store creates the working-directory default.

`process_and_send(self, bundle: ReportingArtifactBundle, *, agreement: AgreementOutcome, counted: bool = True, recipient: str | None = None, subject: str | None = None) -> dict[str, Any]`:

- First calls `assert_reportable`. A counted, unagreed outcome raises `NotAgreedError` directly; warm-up (`counted=False`) passes regardless.
- Rejects a UID already in the pipeline store with `ReportingPipelineError`.
- Calls `bundle.validate_bundle()`, then `bundle.to_attachments()`, which validates the bundle again before serialization. With a configured bundle verifier, every log verifier is therefore called twice. Any `ArtifactError` becomes `ReportingPipelineError` with the original as cause.
- Calls `GmailSender.send_report`; every exception from that call becomes `ReportingPipelineError`.
- Marks the pipeline store only after Gmail returns, then returns Gmail's result unchanged.

There are two independent idempotency layers: this store and the sender's `IdempotencyStore`. A pipeline-store write failure after a successful send propagates unwrapped and can leave the two stores inconsistent.

## Minimal example

```python
from police_peer.reporting.pipeline import settle_series
from police_peer.reporting.schemas import build_series_result

result = build_series_result(
    game_uid="series-placeholder",
    sub_game_results=[],
    total_police_score=1,
    total_thief_score=0,
    tie_applied=False,
    repo_links={},
    total_llm_tokens_per_series=0,
)
assert settle_series(result, result) is result
```
