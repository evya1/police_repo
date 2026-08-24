# Reporting package

The `police_peer.reporting` package turns settled game evidence into JSON artifacts, publishes replay and league-kit directory bundles, optionally reconciles the older internal artifact model, and sends that model through a send-only Gmail adapter. The package does not play games or alter evidence. `police_peer.reporting.__init__` is empty and exports no convenience API; import symbols from their defining modules.

The two artifact models are separate:

- `common.transport.series.SeriesResult` is the runtime result consumed by replay, kit, and settlement modules.
- `police_peer.reporting.schemas.SeriesResult` is the `internal-1` email-pipeline schema consumed by `ReportingArtifactBundle` and `ReportingPipeline`.

Do not interchange these identically named classes.

## Module index

| Python file | Documentation | Purpose |
| --- | --- | --- |
| `__init__.py` | This page | Empty package marker; no public symbols. |
| `schemas.py` | [Schemas and signing](schemas.md) | `internal-1` data classes, builders, validation, signing, and serialization. |
| `artifacts.py` | [Artifact bundles](artifacts.md) | Reconciles exactly 14 `internal-1` email attachments. |
| `gmail.py` | [Gmail delivery](gmail.md) | Send-only Gmail message construction and durable send idempotency. |
| `pipeline.py` | [Reporting pipeline](pipeline.md) | Agreement gate, bundle validation, Gmail delivery, and pipeline idempotency. |
| `replay_documents.py` | [Replay documents](replay-documents.md) | Pure builders for the 15-file `internal-interop-1` replay set. |
| `replay_bundle.py` | [Replay publication](replay-bundle.md) | Atomic publication and self-verification of replay directories. |
| `kit_bundle.py` | [League-kit projection](kit-bundle.md) | Pure build and atomic publication of the league-kit-shaped projection. |
| `settlement.py` | [Settlement](settlement.md) | Result-agreement exchange and non-fatal kit publication orchestration. |

## End-to-end runtime usage

The normal runtime path starts with a completed `common.transport.series.SeriesResult`:

```python
from pathlib import Path

from police_peer.reporting.replay_bundle import publish_replay_bundle
from police_peer.reporting.settlement import publish_kit, settle

# `channel` and `result` come from the completed series runtime.
agreement = settle(channel, result, our_group="group-a", budget=5.0)
replay_dir = publish_replay_bundle(Path("artifacts"), result)
publish_kit(
    Path("artifacts"),
    result,
    our_group="group-a",
    mode="counted",
    confirmed=agreement.agreed,
)
```

Data flows as follows:

1. The series engine returns immutable per-sub-game replay evidence and a six-row ledger in `common.transport.series.SeriesResult`.
2. `settle` derives shared result rows and exchanges a consensus proposal with the opponent. It performs network/channel I/O only when `result.settled` is true.
3. `publish_replay_bundle` builds 15 internal replay JSON files in memory, stages them, reloads and verifies them, then publishes `<artifact_root>/replay/<game_uid>/` with one rename.
4. `publish_kit` projects the same sealed evidence into declaration, six configs, six logs, and one result under `<artifact_root>/kit/<game_uid>/`. Projection errors are logged and suppressed.
5. Separately, callers using the older `internal-1` model can build a `ReportingArtifactBundle` and pass it to `ReportingPipeline.process_and_send`; that path validates 14 attachments and performs Gmail API I/O through `ExternalApiGatekeeper`.

## Configuration and environment

- Install the repository environment with `uv sync --locked --all-groups`; imports assume both `src/` and the repository `common/` package are available.
- Replay and kit APIs take `artifact_root` explicitly. They do not read an environment variable or configuration file.
- Gmail requires an `ExternalApiGatekeeper`, exactly the `gmail.send` OAuth scope (short or full form), a Gmail-compatible service client, and either a default or per-call recipient. This package does not load OAuth files or environment variables itself; composition code must create and inject the client.
- Default idempotency paths are `.sent_game_uids.json` for `GmailSender` and `.sent_reports.json` for `ReportingPipeline`, relative to the process working directory. Supply explicit stores for controlled locations.
- Never put credentials or token values in artifacts. `validate_schema` rejects secret-bearing field names, but it does not inspect arbitrary string values for secrets.

## Outputs and errors

Replay files are indented, sorted-key UTF-8 JSON with a trailing newline. Kit files are indented UTF-8 JSON with a trailing newline. The `internal-1` attachments use compact canonical JSON bytes. Gmail builds a MIME message whose attachments are all declared as `application/json`.

Atomic publishers create missing parent directories, refuse an existing destination, never append, and normally remove staging data on failure. A lock acquired before a later failure is intentionally left for recovery; a pre-existing lock is reported and not removed. See the module pages for exact aliases and failure details.

Key failure families are `ReplayDocumentError`, replay/atomic publication errors, `ArtifactError` and its schema/signature subclasses, Gmail errors, `ReportingPipelineError`, agreement errors from `common.transport.kit_agreement`, and ordinary JSON/filesystem/client exceptions where a module does not translate them. `publish_kit` is the exception: it catches every projection exception, logs an error, and returns `None`.

## Police/Thief parity

The current `origin/master` reporting trees were compared file by file. They contain the same filenames, symbols, signatures, constants, schemas, control flow, and output behavior. Differences are limited to imports from `police_peer...` versus `thief_peer...`; each repository calls its own Gatekeeper and result-agreement adapter. No role-specific reporting field or output format exists in these modules.
