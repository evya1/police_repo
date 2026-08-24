# Settlement (`settlement.py`)

This module derives the result-agreement scope, performs the opponent exchange, and orchestrates a deliberately non-fatal league-kit projection. `NOT_SETTLED` is the exact reason string returned when no settlement occurred.

## Public API

`settlement_rows(result: common.transport.series.SeriesResult, *, our_group: str) -> tuple[list[dict], dict]` maps every ledger row into a per-group result row using `result.opponent_group_id`, zero tokens for both groups, and `log_<game_id>_gNN.json`. It returns `(rows, final)`, where `final` is derived with sorted group IDs and `counted=False`. It performs no I/O. Empty/malformed group IDs or incoherent rows are not prevalidated here; downstream key/settlement exceptions propagate.

`settle(channel, result: SeriesResult, *, our_group: str, budget: float) -> AgreementOutcome` returns `AgreementOutcome(False, NOT_SETTLED)` without channel I/O when `result.settled` is false. Otherwise it builds rows/final, builds a proposal, calls the role-local `wire.result_agreement.exchange(channel, proposal, budget=budget)`, logs the outcome, and returns it. Channel, timeout, proposal, and settlement exceptions propagate.

`publish_kit(artifacts_dir: Path | str, result: SeriesResult, *, our_group: str, mode: str, confirmed: bool, identity: GroupIdentity | None = None, opponent_identity: dict | None = None) -> None` calls `publish_kit_bundle` beside the already-written internal bundle:

- `counted` is true only when `mode == "counted"`.
- With `identity`, it emits sorted public group blocks and computes counted-game totals. A non-integer/missing opponent count becomes `None`; without identity, groups and game counts use kit-builder defaults.
- If replay evidence exists, it parses the first entry's terms and forwards `token_budget_per_series` as `max_tokens_per_game`; otherwise that declaration field is omitted.
- It forwards `confirmed` exactly. It does not forward per-sub-game token counts, `league`, `github`, or `step_zero`.
- Every ordinary `Exception` is caught, logged as an error, and suppressed (`BaseException` subclasses are not caught). The method always returns `None`, so callers cannot distinguish success from failure by return value.

## Minimal example

```python
from police_peer.reporting.settlement import settlement_rows

# `result` is a completed common.transport.series.SeriesResult.
rows, aggregate = settlement_rows(result, our_group="group-a")
assert len(rows) == len(result.ledger)
assert "total_score" in aggregate
```

Ordering is significant: the runtime performs replay publication before `publish_kit`; this module's broad exception handling is intended to preserve the already-written internal evidence if projection fails.
