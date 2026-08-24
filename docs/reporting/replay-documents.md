# Replay documents (`replay_documents.py`)

This pure module converts `common.transport.series.SeriesResult` and `SubgameReplayEvidence` into dictionaries or serialized bytes. It performs no filesystem, clock, network, or email I/O.

The public constants are `SCHEMA_VERSION` (`"internal-interop-1"`), `SCHEMA_STATUS` (`"internal_interop"`), and `SUB_GAME_COUNT` (`6`). `ReplayDocumentError` reports an invalid evidence count, index set, identity, or empty own-record half.

## Input structure

Every evidence entry must have a unique `sub_game_index` making exactly `1..6`, non-empty `game_id` and `game_uid`, and at least one `own_records` item. `terms_bytes` and every `SealedRecord.payload_bytes` must decode as JSON where used. Records contribute decoded payload fields plus `nonce` and `commitment` (emitted as `commit`). Opponent records are optional.

Representative log:

```json
{
  "schema_version": "internal-interop-1",
  "artifact_kind": "log",
  "schema_status": "internal_interop",
  "game_id": "game-placeholder",
  "game_uid": "series-placeholder",
  "sub_game_index": 1,
  "records": [{"step": 0, "action": "STAY", "nonce": "nonce-placeholder", "commit": "digest-placeholder"}],
  "opponent_committed_steps": [0]
}
```

## Builders and helpers

- `build_declaration(result: SeriesResult) -> dict`: base envelope plus `sub_game_count = len(result.ledger)`, `settled`, and string `settled_outcome` or `None`.
- `build_config(evidence: SubgameReplayEvidence) -> dict`: base envelope, `sub_game_index`, and parsed `terms`.
- `build_log(evidence: SubgameReplayEvidence) -> dict`: base envelope, index, flattened own records, sorted observed opponent step numbers, and `opponent_records` only when non-empty.
- `build_result(result: SeriesResult) -> dict`: validates all replay evidence; emits settlement fields, one ledger object per row (`sub_game_number`, role/outcome string values, steps, scores, `audit_ok`), and ordered record-count/final-step summaries.
- `build_manifest(result: SeriesResult, members: list[tuple[str, bytes]]) -> dict`: validates evidence; emits SHA-256 for exactly the supplied member bytes and the ordered record summaries. It does not require a particular member set itself.
- `serialize_document(doc: dict) -> bytes`: sorted-key, indented UTF-8 JSON with a trailing newline. JSON serialization errors propagate.
- `member_filename(kind: str, game_id: str, sub_game_index: int | None = None) -> str`: returns `<kind>_<game_id>.json`, or `<kind>_<game_id>_g<index:02d>.json`; inputs are not validated.
- `build_all_documents(result: SeriesResult) -> dict[str, bytes]`: validates evidence and returns 15 insertion-ordered members: declaration, six configs, six logs, result, then manifest. The manifest hashes the preceding 14 members and is not self-listed.
- `check_completeness(manifest_doc: dict, log_docs: dict[int, dict]) -> list[str]`: returns human-readable mismatches between supplied reloaded logs and manifest counts/final steps. It checks own and expected opponent halves. It only iterates supplied `log_docs`, so absent dictionary entries are not reported by this function alone.

Private helpers `_base`, `_validate_evidence`, `_flatten_record`, `_half_counts`, and `_sub_game_summary` implement those envelopes and counts. Invalid JSON raises `json.JSONDecodeError`; a decoded record payload that is not an object can raise `TypeError`. Evidence validation does not cross-check each evidence identity against the top-level result identity or require `len(result.ledger) == 6`; output uses each source as implemented.

## Minimal example

```python
from police_peer.reporting.replay_documents import build_all_documents

# `result` is a completed common.transport.series.SeriesResult with evidence 1..6.
files = build_all_documents(result)
assert len(files) == 15
assert all(name.endswith(".json") for name in files)
```
