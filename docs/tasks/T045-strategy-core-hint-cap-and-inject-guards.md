---
id: T045
status: ready
priority: P1
task_type: component
component: C02
optional: false
implements:
  - STRAT-008
  - ARCH-007
context_files:
  - docs/PLAN_police_strategy.md
  - docs/decisions/ADR-006-strategy-heuristic-priorities.md
  - src/police_peer/strategy/hints.py
  - src/police_peer/strategy/inject.py
read_set:
  - src/thief_peer/strategy/hints.py
  - src/thief_peer/strategy/inject.py
depends_on:
  - T044
gates: []
parallel_safe: true
claimed_by:
claim_expires_at:
write_set:
  - src/police_peer/strategy/hints.py
  - src/police_peer/strategy/inject.py
  - tests/unit/strategy/test_hints.py
  - tests/unit/strategy/test_inject.py
risk: medium
---

# T045 — Shared-core drift found by the TC-P24 comparison (police_repo)

Newly discovered work, opened by the orchestrator from `T044`'s TC-P24 normalized semantic
comparison of the shared strategy core against `thief_repo`. These are **not** findings from
the 2026-08-22 independent review and were deliberately left out of `T044`'s write set rather
than absorbed silently. Each is a place where `thief_repo` already carries the corrected
behaviour and `police_repo` does not.

## Defects

1. **`hints.py` — a configured `hint_max_words` is ignored.** *(P1 driver: `hint_max_words`
   is one of the 14 negotiated terms in `common/transport/terms.py`, signed at handshake and
   enforced by SPAR-N02/N03. Under the shipped `config/game.json` it is `15`, identical to the
   hard-coded default, so the bug is invisible today — but any organiser shipping another value
   makes this repository breach a term it signed, while `thief_repo` complies.)* `_cap` is a `@staticmethod`
   with `max_words: int | None = None` defaulting to a hard-coded 15, and it is always called
   as `self._cap(text)`. A `HintWriter` built with a smaller cap therefore never truncates to
   it. Repro: `HintWriter(Role.POLICE, Random(0), "New York", 3)._cap("one two three four five six seven")`
   returns all seven words. `thief_repo` makes `_cap` an instance method over `self.max_words`.
2. **`inject.py` — role weight kwargs are applied to any resolved class.** `resolve_brain`
   passes the PoliceBrain-private weights (`min_confidence`, `barrier_mass_floor`, `w_mass`,
   `w_cut`, `route_slack`, `barrier_reserve`, `strong_threshold`, `barrier_score_threshold`)
   to whatever class the selector resolved, so injecting a custom `BrainBase` subclass raises
   `TypeError: BrainBase.__init__() got an unexpected keyword argument 'min_confidence'`.
   `thief_repo` gates the weight vector behind an explicit `issubclass` branch.
3. **`inject.py` — no mapping guard on `strategy`.** `config.get("strategy", {}).get(...)`
   raises `AttributeError` on a non-mapping `strategy` value instead of the documented
   fail-fast `ValueError`/`TypeError`.

## Acceptance criteria

- A `HintWriter` truncates to its configured `hint_max_words`, with a test at a cap below 15.
- A custom `BrainBase` subclass resolves and instantiates without the role weight kwargs;
  `PoliceBrain` still receives them.
- A non-mapping `strategy` value fails fast with the documented error type.
- No Thief weight values are copied into `police_repo`; only the guard shape is aligned.
