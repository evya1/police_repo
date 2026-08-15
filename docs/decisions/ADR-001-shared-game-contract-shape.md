---
artifact: adr
id: ADR-001
status: accepted
date: 2026-08-15
owners: orchestrator
related_requirements: [CFG-001, CFG-002, CFG-003, CFG-004, CFG-005, CFG-006, CFG-007, CFG-008]
related_tasks: [T003, T028]
supersedes:
---

# ADR-001 — Shared game contract (`config/game.json`) section layout and key names

## Context

`CFG-001` requires `config/game.json` to be a shared, byte-for-byte-identical, cryptographically locked contract; `CFG-004` requires every Appendix F value to live in it; `CFG-006`–`CFG-008` fix the Appendix F key names and defaults themselves (`grid_size`, `num_agents`, `max_barriers`, `max_moves`, `survival_threshold`, `move_set`, the scoring keys, and the negotiated defaults). None of the reconstructed source material (`docs/spec/CANONICAL_REQUIREMENTS.md`, the full requirements reconstructions) attests a mandatory section structure, mandatory field grouping, or any field beyond the Appendix F keys themselves — the only Appendix B material referenced by the canonical register concerns shared/private file precedence (`CFG-002`, `CFG-003`), not field layout. Any nesting or nonstandard field beyond the Appendix F register is therefore a **derived engineering choice**, not an official schema, and must be labeled accordingly per `config/README.md`.

Two peers exchanging this file before every series need one agreed physical layout regardless of what the official schema eventually turns out to require, because `CFG-001` demands byte-identical files and `T028` needs a concrete shape to implement against.

## Decision

Adopt a nested-section JSON layout, grouping the Appendix F keys by concern, using the canonical key names already fixed in `docs/spec/CANONICAL_REQUIREMENTS.md` (never a synonym):

```json
{
  "contract_version": "1.0",
  "agreed_between": ["<our-group-code>", "<opponent-group-code>"],
  "board_and_agents": {
    "grid_size": 7,
    "num_agents": 2,
    "thief_start": [3, 3],
    "cop_start": [0, 0],
    "axis_origin_corner": "top-left",
    "axis_start_index": 0
  },
  "movement_and_barriers": {
    "move_set": ["N", "S", "E", "W", "STAY"],
    "max_barriers": 14,
    "max_moves": 35,
    "survival_threshold": 35
  },
  "scoring": {
    "capture_cop": 20,
    "capture_thief": 5,
    "survival_cop": 5,
    "survival_thief": 10,
    "tie_score": 2
  },
  "world": {
    "map_area": "New York",
    "hint_max_words": 15
  },
  "pheromones": {
    "pheromone_center_intensity": 0.9,
    "pheromone_decay": 0.10,
    "pheromone_grid_size": 5
  },
  "network_and_league": {
    "response_timeout_sec": 30,
    "watchdog_timeout_sec": 60,
    "num_games": 6,
    "diversity_reward": 10,
    "min_games_to_pass": 2,
    "max_games_per_team": 10,
    "token_budget_per_series": 200000
  },
  "rate_limiter_gatekeeper": {
    "requests_per_minute": 30,
    "concurrent_requests": 2,
    "retry_backoff_sec": 5,
    "max_retries": 3,
    "queue_depth": 100
  }
}
```

Notes on this decision:

- `contract_version` and `agreed_between` are our own bookkeeping fields, not attested anywhere in the reconstructed source; they exist to let a loader detect a stale or foreign contract file, and are explicitly out of scope for `CFG-004`'s "every Appendix F value" requirement.
- `network_and_league.num_games` is set to the binding `6` (`LEAGUE-001`), not the Appendix B example's demonstration value of `1` — `docs/spec/CANONICAL_REQUIREMENTS.md` and the requirements reconstruction both flag that example value as non-binding.
- No `technical_loss` key is included: it is not an Appendix F table value (no such row exists in table 17); it is a derived outcome of Appendix E rule 48 via `GAME-013`, computed by domain logic rather than read from the contract.
- `move_cap` vs `survival_threshold` are carried as two distinct keys, both defaulting to the binding minimum of 35, exactly as `GAME-014` states — this ADR takes no position on their relationship; that is `OPEN-011`, owned by the lecturer.
- This is a floor, not a ceiling: `CFG-005` permits negotiated tightening/loosening within status rules, so two teams may still amend values (never field names) by agreement.

## Alternatives considered

- **Flat key list matching `docs/spec/CANONICAL_REQUIREMENTS.md` 1:1, no nesting.** Rejected as the *sole* shape for now: it is more literally traceable to the register, but a real interoperability decision on file layout has to be made by two teams before play, and a nested grouping is easier for a human to review during negotiation. The domain/config loader built in `T003`/`T028` reads through named accessors, not raw dict paths, so switching nesting later is a contained change.
- **Deferring the shape entirely as an OPEN item.** Rejected: nothing blocks us from picking our own default while remaining explicit that it is not an official schema; `T028` needs something concrete to implement and test against, and `CFG-009` already requires a uniquely named, committed file per game regardless of shape.

## Consequences

- `T028`'s config loader/validator is written against this exact shape; `T003`'s Appendix F status validator (Fixed/Minimum/Negotiated) operates on the flattened key set regardless of which section a key sits in.
- Because this is a derived choice, `config/README.md` and any example file must carry the `EXAMPLE — NOT AN OFFICIAL ATTACHED TEMPLATE` label until INPUT-001 is verified; if the official schema differs, this file's shape is amended without a Change Request (no approved requirement is contradicted — `CFG-001`/`CFG-004` only constrain what values the contract carries, not its JSON shape).
- No third-party code, configuration, or documentation is copied into this repository as part of this decision; the shape above was authored independently from the canonical requirement register only.

## Validation

- `T028` acceptance criteria include: loading this shape round-trips through the Appendix F status validator from `T003` with no additional/renamed/missing key silently accepted; a private `config/game.toml` key never overrides a signed JSON key (`CFG-003`); and `num_games` in a committed file always reads `6` for counted play.

## Approval

- Decision owner: orchestrator
- Approved by: project team
- Approval date: 2026-08-15
