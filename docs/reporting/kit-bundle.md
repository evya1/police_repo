# League-kit projection (`kit_bundle.py`)

This module projects already sealed `common.transport.series.SeriesResult` evidence into league-kit-shaped JSON. The public constant `KIT_SUBDIR` is `"kit"`. It does not create new game commitments; post-write self-verification recomputes existing record commitments.

## `build_kit_bundle`

```text
build_kit_bundle(
    result: SeriesResult,
    *,
    our_group: str,
    counted: bool,
    groups: list[dict] | None = None,
    step_zero: dict | None = None,
    github: dict | None = None,
    league: dict | None = None,
    max_tokens_per_game: int | None = None,
    tokens_by_sub_game: dict[int, dict[str, int]] | None = None,
    games_played: dict[str, int | None] | None = None,
    first_meeting: bool = True,
    confirmed: bool = False,
) -> dict[str, bytes]
```

`result`, `our_group`, and `counted` are required. The opponent group comes from `result.opponent_group_id`; either group being empty raises `SelfVerifyError`. Evidence is processed in `sub_game_index` order and paired with `result.ledger` by `sub_game_number`.

For a normal six-sub-game result, output has 14 members: `declaration_<game_id>.json`, six `config_<game_id>_gNN.json`, six `log_<game_id>_gNN.json`, and `result_<game_id>.json`. Bytes are indented UTF-8 JSON with a trailing newline and insertion-order keys.

- `groups=None` emits two `{ "group_id": ... }` blocks sorted by ID; an explicit list is passed through to declaration validation and must contain two entries.
- Each config parses the exact sealed `terms_bytes` and includes the terms and their canonical SHA-256.
- Each log contains a summary, wrapped own records, optional wrapped opponent records, and sorted opponent-committed steps.
- Missing `tokens_by_sub_game` entries default both groups to zero.
- `games_played`, `first_meeting`, and `counted` feed the derived final aggregate. `github`, `league`, `step_zero`, and `max_tokens_per_game` are omitted when `None` by the downstream builders.
- `confirmed` is recorded in the mutual-agreement block; it is never inferred.

Representative record envelope:

```json
{
  "payload": {"step": 0, "action": "STAY"},
  "nonce": "nonce-placeholder",
  "commit": "digest-placeholder"
}
```

The function is pure with respect to filesystem/network/clock. JSON decode errors, missing ledger rows (`KeyError`), malformed record errors, settlement errors, and downstream builder errors propagate. It does not independently require exactly six evidence rows; the 14-file count follows from a valid six-entry runtime result. With no replay evidence and non-empty group IDs it can build only declaration and result files.

## Publication

`publish_kit_bundle(artifact_root: Path | str, result: SeriesResult, *, on_checkpoint: Checkpoint | None = None, **kwargs) -> Path` forwards `kwargs` to `build_kit_bundle`, then atomically publishes at `<artifact_root>/kit/<game_uid>/`. The parent is created; an existing destination is rejected, never overwritten or appended. After staging, `_self_verify` reloads every existing `log_*.json` and recomputes every own/opponent `commit`; mismatches raise `SelfVerifyError`. It does not check an expected log count, so it does not reject the empty-evidence two-file case by itself. Atomic publication and checkpoint failures behave as described in [Replay publication](replay-bundle.md).

Private `_records` decodes sealed payload bytes and wraps them, `_document_bytes` serializes JSON, `_audit_block` derives the log audit summary, and `_self_verify` performs the post-write check.

## Minimal example

```python
from police_peer.reporting.kit_bundle import build_kit_bundle

# `result` is a completed common.transport.series.SeriesResult.
files = build_kit_bundle(result, our_group="group-a", counted=False)
assert "result_" in next(name for name in files if name.startswith("result_"))
```
