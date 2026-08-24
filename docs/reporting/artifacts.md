# Artifact bundles (`artifacts.py`)

`ReportingArtifactBundle` reconciles the `internal-1` schema objects and converts them to ordered Gmail attachments. It performs validation and serialization only; it does not write files or send email.

## Public API

`ReportingArtifactBundle` is a dataclass with required `declaration: Declaration`, `sub_game_configs: list[SubGameConfig]`, `sub_game_logs: list[SubGameLog]`, and `series_result: reporting.schemas.SeriesResult`. Optional `verifier: Callable[[bytes, str], bool] | None = None` enables mandatory signature checking for every finalized log.

- `validate_bundle(self) -> None` requires exactly six configs and six logs; validates declaration and result schemas and shared `game_uid`; then pairs config/log entries by list order, validates both schemas and identifiers, requires each log to be finalized, and, if `verifier` is set, requires and verifies each log signature. It does not sort or match pairs by index; caller ordering is significant.
- `to_attachments(self) -> list[tuple[str, bytes]]` calls `validate_bundle`, then returns 14 `(filename, canonical_json_bytes)` pairs in this order: declaration, six configs in input order, six logs in input order, result. It writes nothing.

`SchemaError` is raised for count, schema, identifier, finalization, missing-signature, or failed-verification faults. Exceptions from a supplied verifier or serialization propagate.

## Minimal example

```python
from police_peer.reporting.artifacts import ReportingArtifactBundle

# `declaration`, six ordered `configs`, six finalized ordered `logs`, and
# `series_result` are instances from police_peer.reporting.schemas.
bundle = ReportingArtifactBundle(declaration, configs, logs, series_result)
attachments = bundle.to_attachments()
assert len(attachments) == 14
```

Every filename follows `artifact_filename`; returned bytes are in memory and no destination path is created, replaced, or appended.
