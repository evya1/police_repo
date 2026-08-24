# Schemas and signing (`schemas.py`)

This module defines the older internal email-artifact schema, version `SCHEMA_VERSION = "internal-1"`. It is independent of `common.transport.series.SeriesResult` and performs no filesystem, network, or email I/O.

## Exceptions

`ArtifactError` is the base class. `SchemaError` reports invalid identifiers, versions, lifecycle stages, fields, types, extra fields, or secret-bearing keys. `SignatureError` reports a missing signer/verifier. `IdentifierMismatchError` reports cross-artifact `game_uid` or sub-game `game_id` mismatch. `FinalizedLogMutationError` reports assignment to a finalized log or a second finalization.

## Data classes

All fields have dataclass defaults, but constructors for `Declaration`, `SubGameConfig`, and `SubGameLog` immediately require the identifiers noted below. Each class exposes read-only `artifact_id` and `as_dict() -> dict[str, Any]`. The mapping uses the exact fields listed below. Declaration, config, and result return their nested list/dictionary objects by reference; log shallow-copies `steps` to a list.

### `Declaration`

| Field | Type | Default / constraint |
| --- | --- | --- |
| `kind` | `str` | `"declaration"` |
| `game_uid` | `str` | `""`; actually required and non-empty at construction |
| `schema_version` | `str` | `SCHEMA_VERSION`; no other value accepted |
| `team`, `role`, `hardware`, `model`, `start_time`, `end_time` | `str` | `""` |
| `members`, `mcp_addresses` | `list[str]` | new empty list |
| `police_repo_url`, `thief_repo_url` | `str` | `""` |
| `token_budget` | `int` | `0` |
| `num_games` | `int` | `6`; `validate_schema` requires non-negative |

`artifact_id` is `game_uid`.

### `SubGameConfig`

Fields are `kind: str = "sub_game_config"`, required non-empty `game_uid: str`, required non-empty `game_id: str`, `schema_version: str = SCHEMA_VERSION`, `sub_game_index: int = 0`, `role_for_this_sub_game: str = ""`, `agreed_terms: dict[str, Any] = {}`, and required non-empty `git_commit: str`. `artifact_id` is `<game_uid>:<game_id>`.

### `SubGameLog`

Fields are `kind: str = "log"`, required non-empty `game_uid: str`, required non-empty `game_id: str`, `schema_version: str = SCHEMA_VERSION`, `steps: list[dict[str, Any]] = []`, `finalized: bool = False`, and `signature: str | None = None`. `artifact_id` is `<game_uid>:<game_id>`.

After `finalize_log`, `steps` is a tuple in the live object but `as_dict` emits it as a JSON list. Any normal attribute assignment while `finalized` is true raises `FinalizedLogMutationError`.

Representative declaration, config, and log shapes (placeholder values):

```json
{
  "kind": "declaration",
  "game_uid": "series-placeholder",
  "schema_version": "internal-1",
  "team": "team-placeholder",
  "role": "police",
  "members": ["member-placeholder"],
  "police_repo_url": "https://example.invalid/police",
  "thief_repo_url": "https://example.invalid/thief",
  "mcp_addresses": ["https://example.invalid/mcp"],
  "hardware": "hardware-placeholder",
  "model": "model-placeholder",
  "token_budget": 0,
  "start_time": "time-placeholder",
  "end_time": "time-placeholder",
  "num_games": 6
}
```

```json
{"kind":"sub_game_config","game_uid":"series-placeholder","game_id":"subgame-placeholder","schema_version":"internal-1","sub_game_index":1,"role_for_this_sub_game":"police","agreed_terms":{"board_size":7},"git_commit":"commit-placeholder"}
```

```json
{"kind":"log","game_uid":"series-placeholder","game_id":"subgame-placeholder","schema_version":"internal-1","steps":[{"step":1,"action":"STAY"}],"finalized":true,"signature":"signature-placeholder"}
```

### `SeriesResult`

This is `police_peer.reporting.schemas.SeriesResult`, not the runtime series type. Its fields are `kind: str = "result"`, required non-empty `game_uid: str`, `schema_version: str = SCHEMA_VERSION`, `sub_game_results: list[dict[str, Any]] = []`, `total_police_score: int = 0`, `total_thief_score: int = 0`, `tie_applied: bool = False`, `repo_links: dict[str, str] = {}`, `total_llm_tokens_per_series: int = 0`, `sub_game_git_commits: dict[str, str] = {}`, and `total_llm_tokens_per_sub_game: dict[str, int] = {}`. `artifact_id` is `game_uid`.

Representative result structure:

```json
{
  "kind": "result",
  "game_uid": "series-placeholder",
  "schema_version": "internal-1",
  "sub_game_results": [{"game_id": "subgame-placeholder", "outcome": "placeholder"}],
  "total_police_score": 1,
  "total_thief_score": 0,
  "tie_applied": false,
  "repo_links": {"police": "https://example.invalid/police"},
  "total_llm_tokens_per_series": 0,
  "sub_game_git_commits": {"1": "commit-placeholder"},
  "total_llm_tokens_per_sub_game": {"1": 0}
}
```

The open dictionaries and lists have no deeper value schema here. Validation checks their container types and recursively rejects keys whose names contain a configured secret token.

## Builders

- `build_declaration(*, game_uid: str, team: str, role: str, members: list[str], police_repo_url: str, thief_repo_url: str, mcp_addresses: list[str], hardware: str, model: str, token_budget: int, start_time: str, end_time: str, num_games: int = 6) -> Declaration`: all keyword-only inputs are required except `num_games`. Construction validates only `game_uid` and schema version; call `validate_schema` for full top-level type checks.
- `build_sub_game_config(*, game_uid: str, game_id: str, sub_game_index: int, role_for_this_sub_game: str, agreed_terms: dict[str, Any], git_commit: str) -> SubGameConfig`: all inputs required; construction validates both IDs, commit non-emptiness, and schema version.
- `build_sub_game_log(*, game_uid: str, game_id: str, steps: list[dict[str, Any]] | None = None) -> SubGameLog`: `steps=None` or an empty list produces a new empty list; validates both IDs and version.
- `build_series_result(*, game_uid: str, sub_game_results: list[dict[str, Any]], total_police_score: int, total_thief_score: int, tie_applied: bool, repo_links: dict[str, str], total_llm_tokens_per_series: int, sub_game_git_commits: dict[str, str] | None = None, total_llm_tokens_per_sub_game: dict[str, int] | None = None) -> SeriesResult`: optional maps become new empty dictionaries when falsey.

## Validation and lifecycle API

- `assert_lifecycle_ok(artifact: Any, stage: str) -> None`: accepts stages `pre_series`, `pre_sub_game`, `during_sub_game`, and `post_settlement`. Declaration is only `pre_series`; config only `pre_sub_game`; log `pre_sub_game` or `during_sub_game`; result only `post_settlement`. Unknown stage/type raises `SchemaError`.
- `validate_schema(artifact: Any) -> None`: requires `as_dict`, rejects secret-bearing keys with the traversal described below, then enforces the exact top-level field set and container/scalar types for the four classes. Extra or missing fields raise `SchemaError`. Nested value shapes are otherwise not validated. It does not re-run the constructor's identifier or exact-version validators, so later mutation to a different non-empty identifier or another string version is not caught here. Python's `isinstance` rules apply, so `bool` also satisfies fields checked as `int`.
- `validate_identifiers(*artifacts: Any) -> None`: no arguments is a no-op. Otherwise all objects' `game_uid` attributes must match; all `SubGameConfig` and `SubGameLog` objects in that call must share `game_id`. Missing attributes participate as `None`. It does not compare a declaration/result to a sub-game `game_id` because those types have none.

Secret detection is key-name based and case-insensitive. `_SECRET_KEY_TOKENS` contains substrings for password, secret, credential, API/private/access keys, refresh/access/auth tokens, bearer, client secret, and OAuth. Traversal follows dictionaries and dictionary items directly inside lists/tuples; a list nested directly inside another list is not descended into. String values are not scanned.

## Signing, finalization, and serialization

- `sign_artifact(artifact: Any, signer: Callable[[bytes], str]) -> str`: calls `artifact.as_dict()`, replaces any `signature` field with `None`, canonicalizes the payload, and returns `signer(data)`. A `None` signer raises `SignatureError`; signer exceptions propagate.
- `verify_artifact(artifact: Any, signature: str, verifier: Callable[[bytes, str], bool]) -> bool`: returns `False` for an empty/non-string signature; otherwise calls the verifier with the same canonical payload. A `None` verifier raises `SignatureError`; verifier exceptions propagate.
- `finalize_log(log: SubGameLog, signer: Callable[[bytes], str]) -> SubGameLog`: ordering is required: add all steps first, then finalize once. It converts `steps` to a tuple, sets `finalized=True`, signs that state, stores the signature, and returns the same object. On signing failure it resets `finalized=False` and `signature=None` but leaves `steps` as a tuple.
- `serialize(artifact: Any) -> bytes`: returns compact deterministic canonical JSON bytes from `as_dict`; it does not validate first and writes no file.
- `artifact_filename(artifact: Any) -> str`: returns `<kind>_<game_uid>_<game_id-or-series>.json`, using `artifact`, an empty UID, and `series` fallbacks where attributes are missing. It performs no validation.

## Minimal example

```python
from police_peer.reporting.schemas import (
    build_sub_game_log,
    finalize_log,
    serialize,
    validate_schema,
)

log = build_sub_game_log(
    game_uid="series-placeholder",
    game_id="subgame-placeholder",
    steps=[{"step": 1, "action": "STAY"}],
)
finalize_log(log, lambda payload: "signature-placeholder")
validate_schema(log)
json_bytes = serialize(log)
```
