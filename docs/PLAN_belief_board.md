---
artifact: stage-plan
id: PLAN-BELIEF-BOARD
status: draft — pending orchestrator approval (workflow step 5, guidelines p. 9 §2.5)
version: 0.1
derived_from: PRD-BELIEF-BOARD@0.1 · M-02-belief-state · ADR-004
applies_to: police_repo + thief_repo — one shared belief board; role-agnostic code, role-parameterized only by package import path
owner: orchestrator
updated: 2026-08-20
---

# PLAN — Belief Board (Stage 3, shared part)

## 1. Approach summary

One pure module per repository — `src/thief_peer/belief/` and `src/police_peer/belief/` —
holding a normalized probability grid over the opponent's cell, updated every half-turn by
four pure steps in a fixed order: **exclude → diffuse → observe → hint** (self-exclusion last,
gated). The module is role-agnostic: the role never enters the update, so both repositories
carry the same files modulo package import paths (the shared-scent precedent). It depends
only on `common.domain` (board geometry, `Cell`) and one narrow Protocol — the scent
**emission probe** (FR-B9) — supplied by the already-delivered scent module, so the
likelihood stays calibrated to the *locked* profile without a profile branch in `belief/`.

Integration is top-down over the stage-2 spine (PLAN-MCP-INFRA §12 stub-replacement
discipline): the role glue already carries a stand-in decision engine and a placeholder
belief (SD-03). This stage replaces the placeholder with the real `BeliefGrid` in the turn
handler's update path, and the spine test
(`tests/integration/test_series_loopback.py`) must stay green after every replacement.
Nothing in this PLAN builds toward the strategy's internals — the strategy reads a snapshot
(§5.4) and owns its own files in the role-specific PLANs.

Binding integration strategy:

1. Build the grid + invariants first, against plain data (no transport).
2. Wire the real board into the turn handler; spine green.
3. Add the hint channel last (it is the only part with a cross-repo shared table that the
   strategy's hint generator will also import).
4. Property/differential/perf suites close the stage.

## 2. C4 — Level 1: Context

```mermaid
flowchart LR
    subgraph this peer process
        BELIEF[Belief Board<br/>src/&lt;role&gt;_peer/belief/]
    end
    OPPONENT[Opponent peer<br/>(sends scent grid, hint, barrier declarations)]
    STRAT[Role strategy<br/>(consumer: snapshot)]
    GUI[Live GUI<br/>(consumer: as_matrix, OBS-003)]
    SCS[Shared config<br/>game.json signed + game.toml private]
    OPPONENT -- "TurnMessage: smell_grid, hint, barrier_placed (CT-03)" --> BELIEF
    SCS -- "board size, move set, arena, [belief] tuning" --> BELIEF
    BELIEF -- "peak, top_k, prob, confidence" --> STRAT
    BELIEF -- "as_matrix()" --> GUI
```

External actors: the opponent peer (evidence source — never a data source for *truth*), the
signed constitution, the private tuning file. The belief board has no other external
dependency: no network, no disk, no clock.

## 3. C4 — Level 2: Container (one peer process)

```mermaid
flowchart TB
    subgraph peer process
        subgraph C04 runtime reliability (assumed delivered)
            TH[TurnHandler — update path]
            TS[TurnSender — decision path]
            SM[Orchestrator FSM]
        end
        subgraph C02 perception strategy
            subgraph belief [belief/ — THIS PLAN]
                GRID[grid.py]
                UPD[update.py]
                HINTS[hints.py — landmark registry]
                PROBE[probe.py — emission-probe Protocol]
            end
            STRATBOX[strategy/ — role-specific PLAN]
            SCENTBOX[scent/ — delivered, provides probe impl]
        end
        C01[common.domain — Board, Cell, GameEngine]
        TH --> UPD
        TS --> STRATBOX
        STRATBOX --> GRID
        HINTS -. "same landmark table" .- HINTGEN[strategy hint generator]
        SCENTBOX --> PROBE
        C01 --> GRID
        C01 --> UPD
    end
```

Dependency direction is strictly inward: `belief/` never imports `strategy/`, `wire/`,
`transport/`, or `ui/`. The dashed line is the *content* sharing (one landmark table) —
implemented as an import from `belief.hints` by the strategy's hint generator, never as a
copy.

## 4. C4 — Level 3: Component

| Module | Responsibility | Owns state? |
|---|---|---|
| `belief/grid.py` | The distribution: init, `prob`, `most_likely`, `top_k`, `peak_probability`, `exclude`, `as_matrix`, private `_normalize` | yes — the one mutable object |
| `belief/update.py` | Pure update functions: `diffuse`, `observe_smell` (both forms), composition helper `apply_half_turn` | no |
| `belief/hints.py` | Landmark registry (`LANDMARK_CELLS` per arena + generic compass fallback), `parse_landmarks(hint, arena) -> list[Cell]` (pure), `apply_hint(grid, hint, arena, reliability)` | no (table is const) |
| `belief/probe.py` | `EmissionProbe` Protocol + the `kernel_bayes` scored-likelihood function that consumes it | no |
| `belief/__init__.py` | `BeliefGrid` construction from (board, private config, probe) — the only public entry | no |

State ownership rule (AGENTS.md): the only mutable state is `grid._probs` (a list of lists);
everything else is a pure function. The grid's normalizer resets to uniform on a degenerate
(~0) total instead of dividing by zero — a defensive invariant, tested.

## 5. C4 — Level 4: Code (module APIs)

Signatures as they will exist; bodies are the task-level detail (TODO_belief_board).

### 5.1 `belief/grid.py`

```python
_EPSILON = 1e-9

class BeliefGrid:
    """Normalized P(opponent = cell) over an NxN board. Local inference only."""

    def __init__(self, board: Board, *, trust: float = 4.0,
                 update_form: str = "trust_v1",
                 hint_reliability: float = 0.25,
                 probe: EmissionProbe | None = None) -> None: ...
    # update_form "kernel_bayes_v1" without a probe raises ValueError (fail fast).

    # -- queries (FR-B6) -------------------------------------------------
    def prob(self, cell: Cell) -> float: ...
    def most_likely(self) -> Cell: ...        # argmax, tie: lexicographic (row, col)
    def peak_probability(self) -> float: ...
    def top_k(self, k: int) -> list[tuple[Cell, float]]: ...
    def as_matrix(self) -> list[list[float]]: ...  # deep copy (OBS-003 verbatim)

    # -- updates (called by update.py; kept public for testability) -------
    def exclude(self, cell: Cell) -> None: ...  # zero + renormalize (FR-B4)
    def diffuse(self) -> None: ...               # FR-B3, neighbourhood from board move set
    def observe_smell(self, field: dict[str, float]) -> None: ...  # FR-B2, selected form
    def apply_hint(self, hint: str, arena: str) -> None: ...       # FR-B5 via hints.py
```

Construction takes the C01 `Board` (not a bare size) so the diffusion neighbourhood and
`in_bounds` come from the signed geometry (FR-B3). The probe is injected only for
`kernel_bayes_v1`; `trust_v1` boards never see a probe (the seam is unused, not stubbed).

### 5.2 `belief/update.py` (pure functions)

```python
def diffuse(probs: list[list[float]], offsets: list[Cell]) -> list[list[float]]:
    """Spread each cell's mass uniformly over its in-bounds neighbourhood (incl. self)."""

def observe_trust(probs, field: dict[str, float], trust: float, size: int) -> list[list[float]]:
    """b(cell) *= (1 + trust * intensity) for received cells; renormalize. (trust_v1)"""

def observe_kernel(probs, field: dict[str, float], trust: float, size: int,
                   probe: EmissionProbe) -> list[list[float]]:
    """Full emission-model likelihood against probe.field_at(hypothesis) per cell.
    Reduces to: factor(s) = 1 + trust * (fit(s) - 0.5), fit in [0,1] normalized over
    the field's cells; field-absent hypotheses get factor < 1 (negative evidence)."""

def apply_half_turn(grid: BeliefGrid, *, barrier: Cell | None, field: dict[str, float],
                    hint: str, arena: str, own_cell: Cell, capture_landed: bool) -> None:
    """THE fixed order (PRD §8.1):
    1. exclude(barrier)        [if barrier is not None]
    2. diffuse()
    3. observe_smell(field)
    4. apply_hint(hint, arena)
    5. exclude(own_cell)       [if not capture_landed]
    """
```

`apply_half_turn` is the single composition point the turn handler calls — the order lives
in exactly one place (DRY), and tests pin it.

### 5.3 `belief/hints.py` (shared table + pure parser)

```python
# The ONE landmark table, both directions: belief reads it to interpret hints,
# the strategy's hint generator reads it to produce them.
LANDMARK_CELLS: dict[str, dict[str, list[Cell]]] = {
    "New York": {
        "The Bronx":     [(0, 0), (0, 1), (1, 0)],
        "Central Park":  [(1, 2), (1, 3), (1, 4)],
        "Manhattan":     [(2, 2), (3, 2), (4, 2)],
        "Times Square":  [(3, 3), (3, 4), (4, 3)],
        "Brooklyn":      [(5, 4), (6, 4), (6, 5)],
    },
    # unknown arena -> GENERIC_FALLBACK (compass words -> corners/edges/centre of the board)
}
GENERIC_FALLBACK: dict[str, tuple[Cell, ...]] = {
    "north": ..., "south": ..., "east": ..., "west": ..., "center": ...,  # board-relative
}

def parse_landmarks(hint: str, arena: str, board_size: int) -> list[Cell]:
    """Case-insensitive substring match of registered landmark names (and compass words
    for unregistered arenas). Returns the matched region cells (may be empty). Pure."""

def apply_hint(grid: BeliefGrid, hint: str, arena: str, board_size: int) -> None:
    """For each matched cell at Chebyshev distance d: b *= (1 + rel * w(d)),
    w(0)=1, w(1)=0.5; renormalize. Empty match: no-op."""
```

Table placement note: the region cells are a **project convention** (not official, not
signed) — the book fixes the arena *name* (New York) and the word cap, not the board
mapping. Both repositories must carry the identical table (TC-B11 sync check); changing it
is a shared-code change handled by the orchestrator in both repos.

### 5.4 `belief/probe.py`

```python
class EmissionProbe(Protocol):
    """Narrow seam to the locked scent profile (FR-B9, ADR-004)."""
    def field_at(self, center: Cell) -> dict[str, float]:
        """Pure radial emission at a hypothetical centre, per the LOCKED profile,
        in-bounds cells only, wire spelling {"r,c": intensity}. No state mutation."""

def kernel_factors(size: int, field: dict[str, float], probe: EmissionProbe,
                   trust: float) -> list[list[float]]:
    """Per-hypothesis-cell likelihood factor for the received field (see §5.2)."""
```

The scent module implements the probe per profile: `subtractive_chebyshev_v1` reuses its
existing `smell_emit` (already a pure function of the centre); `multiplicative_book_v1`
reuses the verbatim figure-4 kernel lookup. That implementation is the small additive seam
of FR-B9 (orchestrator records it against T005 or a follow-on task before BB-03).

### 5.5 `belief/__init__.py`

```python
def build_belief(board: Board, cfg: Mapping[str, object],
                 probe: EmissionProbe | None) -> BeliefGrid:
    """Reads only the [belief] private keys (smell_trust_weight, update_form,
    hint_reliability) off the resolved config mapping — no file I/O here; the config
    manager (C01, delivered) does the loading. Unknown update_form -> ValueError."""
```

## 6. UML — Sequence: one half-turn at the update path

```mermaid
sequenceDiagram
    participant RT as TurnHandler (C04)
    participant W as update.apply_half_turn
    participant G as BeliefGrid
    participant H as hints
    participant P as probe (scent)
    RT->>W: (barrier?, smell_grid, hint, arena, own_cell, capture_landed)
    W->>G: exclude(barrier) [if present]
    W->>G: diffuse()  (neighbourhood from board move set)
    W->>G: observe_smell(field)
    alt update_form == kernel_bayes_v1
        G->>P: field_at(hypothesis) for each live hypothesis
        P-->>G: per-hypothesis kernel
        G->>G: kernel likelihood, renormalize
    else trust_v1 (default)
        G->>G: b *= (1 + trust*i) on field cells, renormalize
    end
    W->>H: parse_landmarks(hint, arena)
    H-->>W: matched region cells (may be [])
    W->>G: apply_hint via matched cells (no-op if [])
    W->>G: exclude(own_cell) [if not capture_landed]
    Note over G: normalized after each step; snapshot stable for the strategy
```

## 7. UML — Flow: update-order and edge handling

```mermaid
flowchart TD
    A[incoming half-turn evidence] --> B{barrier declared?}
    B -- yes --> B1[exclude barrier cell]
    B -- no --> C
    B1 --> C[diffuse: spread over self + 4 ortho in-bounds]
    C --> D{received field empty?}
    D -- yes, trust_v1 --> E[no-op: one-sided likelihood carries no negative evidence]
    D -- yes, kernel --> E2[negative evidence: factors < 1 off any support]
    D -- no --> F[likelihood update on field cells]
    E --> G
    E2 --> G
    F --> G{hint names a registered landmark / compass word?}
    G -- yes --> H[b *= 1 + rel*w(d) on region cells]
    G -- no --> I[no-op: neutral hint is not evidence]
    H --> J
    I --> J{capture landed this turn?}
    J -- no --> K[exclude own cell]
    J -- yes --> L[keep own cell live]
    K --> M[renormalized snapshot]
    L --> M
```

Edge cases pinned by tests: all-zero field (E/E2), off-board cells in a malformed field
(ignored), hint with no landmark (I), barrier == own cell (both exclusions compose),
degenerate total → uniform reset in the normalizer.

## 8. UML — State: belief lifecycle per sub-game

```mermaid
stateDiagram-v2
    [*] --> Uniform: build_belief (fresh per sub-game)
    Uniform --> Updated: first half-turn evidence
    Updated --> Updated: exclude -> diffuse -> observe -> hint -> (self-exclude)
    Updated --> Frozen: terminal outcome (capture / survival / zeroed)
    Frozen --> [*]: discarded at sub-game end (no cross-sub-game state)
    note right of Updated: invariants hold in every state; "Frozen" is read-only for audit/GUI
```

## 9. Deployment

In-process; nothing to deploy. The module adds no ports, no files, no environment
variables. Both repositories ship it independently (environment separation, ARCH-001/002).

## 10. Data Contracts (no wire of its own)

The belief board **sends nothing** and **receives nothing** directly on the wire — it sits
behind the already-delivered CT-03 envelope:

| Direction | Contract | Fields touched |
|---|---|---|
| in | CT-03 `TurnMessage` (via the turn handler) | `smell_grid` (`{"r,c": intensity}`), `hint` (≤ 15 words), `barrier_placed` (`[r,c]` or absent) |
| in | CT-01 local state | own cell; "capture landed" flag from the C04 turn loop |
| out | CT-02 decision request (to the strategy) | belief snapshot: `most_likely`, `peak_probability`, `top_k`, `prob` |
| out | CT-05 event projection (to the GUI) | `as_matrix()` verbatim (OBS-003) |

Additive-only rule (CT-02/CT-05): the snapshot fields above are the whole surface; the
strategy's PLAN may not invent new belief outputs without a contract change.

## 11. Configuration

Per PRD §9: private `[belief]` keys (`smell_trust_weight`, `update_form`,
`hint_reliability`), consumed through the C01 config manager's resolved mapping (no file
I/O in `belief/`). Shared signed values consumed: `board_and_agents.grid_size`,
`movement_and_barriers.move_set`, `world.map_area`. Precedence: shared JSON overlays
private TOML on conflict; `[belief]` keys have no shared counterparts.

## 12. Integration Spine — Stub Replacement Map

Continues the stage-2 discipline (PLAN-MCP-INFRA §12, SD-03 stand-in engine):

| Step | Replace | With | Spine invariant |
|---|---|---|---|
| S1 | placeholder belief object in the role glue's turn handler | real `BeliefGrid` + `apply_half_turn` | `tests/integration/test_series_loopback.py` green |
| S2 | stand-in engine's "belief" reads (if any) | real snapshot reads (`most_likely`, `peak_probability`) | same spine green; stand-in movement unchanged until the role-specific strategy stage swaps it |
| S3 | — (hint table) | `belief/hints.py` table imported by the strategy hint generator (role PLAN step) | both repos' sync check green |

The belief stage finishes with S1+S2 done and the spine green; the strategy stage then
replaces the stand-in *decision* on top of the real belief. No big-bang: each swap is its
own task with its own green run (TODO_belief_board BB-02…BB-06).

## 13. Stage Decisions (promote to ADRs only if the orchestrator wants durable records)

### SD-B1 — Default `trust_v1`, optional `kernel_bayes_v1`, selected at construction

**Decision:** ship the reference-compatible one-sided trust form as default; register the
full emission-model form behind `belief.update_form`; no mid-sub-game switching.
**Rationale:** ADR-004 discipline — the reference-reproducible behaviour is the safe
default; the upgrade is the legitimate headroom the reference report identifies, and the
seam (FR-B9) keeps it cheap. **Trade-off:** the default tolerates stale hotspots (empty
field = no evidence); the optional form fixes it at ~1.2k flops per update (inside budget).
**Alternatives:** kernel-default (rejected: unproven against the reference on league
fixtures), particle filter (rejected: breaks determinism without seeding, overkill).

### SD-B2 — Fixed update order: exclude → diffuse → observe → hint → self-exclude

**Decision:** the order is pinned in `apply_half_turn` (PRD §8.1).
**Rationale:** excluding barriers *before* diffusion keeps barrier mass from leaking back
onto the excluded cell in the same half-turn (a barrier placed this turn must be hard
before the transition spreads); observing *after* diffusion matches the physics (the
opponent moved, then we see the field it left); self-exclusion last is gated on
"no capture landed" because a landed capture is exactly the case where the opponent *was*
on our cell. **Alternatives:** observe-before-diffuse (rejected: the reference order and
the E1 worked example use diffuse-then-observe; deviating breaks the differential test).

### SD-B3 — Landmark table lives in `belief/hints.py`, shared by both directions

**Decision:** the belief module owns the table; the strategy's hint generator imports it.
**Rationale:** one source of truth (DRY); the table is inference knowledge (how *I* read
hints), which is belief territory; both repos carry it identically (sync check TC-B11).
**Trade-off:** the strategy module has an import into `belief/` — acceptable: it is a
const table, not strategy logic, and the alternative (two copies) is exactly the drift
this project forbids.

### SD-B4 — `BeliefGrid` takes the C01 `Board`, not a size

**Decision:** construction via the `Board` object; neighbourhood/bounds from it.
**Rationale:** the signed move set is already parsed into the Board (C01); passing a size
would fork the geometry and re-introduce a second source of truth. **Trade-off:** one more
object in the constructor; negligible.

### SD-B5 — No RNG in the board

**Decision:** the belief module is fully deterministic; all stochasticity (hint truth/lie,
any future exploration) belongs to the strategy's seeded RNG.
**Rationale:** the board is inference, not behaviour; determinism makes the differential
and property tests exact and keeps the sealed transcript reproducible.

## 14. Requirement → Module → Test Traceability

| Req | Module (file.function) | Tests |
|---|---|---|
| STRAT-001 (belief map) | `grid.py` (init, all queries), `update.py` | TC-B01, TC-B02, TC-B13, TC-B15 |
| STRAT-006 (updated from scent **and hints**, influences selection) | `update.py:observe_*`, `hints.py:apply_hint`, `update.py:apply_half_turn` | TC-B05…B10, TC-B15 |
| M-02 inv. 1 (normalization) | `grid.py:_normalize` | TC-B02, TC-B16 |
| M-02 inv. 2 (impossible cells zero) | `grid.py:exclude` | TC-B03, TC-B04 |
| M-02 inv. 3 (no hidden truth) | whole-module API + static scan | TC-B12 |
| M-02 inv. 4 (evidence never discarded) | `update.py` (every step applied; neutral hint = explicit no-op, not drop) | TC-B02, TC-B10 |
| STRAT-005 / ADR-004 (locked profile, profile-agnostic) | `probe.py` + scent seam impl | TC-B08 |
| CFG-006 (consume signed scent values) | `__init__.py:build_belief`, `probe.py` | TC-B06, TC-B08 |
| OBS-002 (no opponent state to logs/GUI) | whole-module API | TC-B12, TC-B16 |
| OBS-003 (verbatim heatmap) | `grid.py:as_matrix` | TC-B16 |
| NFR-1 (≤ 5 ms) | all | TC-B14 |
| NFR-2 (determinism) | all | TC-B13 |

## 15. Verification Commands

```sh
uv sync --locked --all-groups
uv run pytest tests/unit/belief -q            # unit: TC-B01…B11, TC-B16
uv run pytest tests/property/belief -q        # property: TC-B02 (10k sequences)
uv run pytest tests/unit/belief/test_differential.py -q   # TC-B06…B08 (reference vectors)
uv run pytest tests/integration/test_series_loopback.py -q  # spine green after S1/S2
uv run ruff check src/thief_peer/belief tests/unit/belief tests/property/belief
uv run python -m tests.tooling.line_cap src/thief_peer/belief   # ≤ 150 nonblank/noncomment
# same commands with police_peer/ in police_repo
# cross-repo: shared-file sync check (belief/*.py identical modulo package import path)
```

## 16. Relationship to the Repository Documents

- **Upstream:** `PRD-BELIEF-BOARD` (this stage's PRD); M-02 (binding invariants);
  C02 component PRD/PLAN (shared scope); ADR-004 (locked profile, profile-agnostic
  consumption); CT-01/02/03/05 (boundaries).
- **Siblings (same stage, separate files):** `PRD/PLAN/TODO_thief_strategy.md` (thief_repo)
  and `PRD/PLAN/TODO_police_strategy.md` (police_repo) — the role-specific consumers.
  This PLAN owns the belief half of Stage 3; the role PLANs own the strategy half. They
  share the landmark table (SD-B3) and nothing else.
- **Execution:** `TODO_belief_board.md` (this stage's ledger) maps to repo task **T006**
  (write set `src/<role>_peer/belief/`, `tests/unit/belief/`) plus the FR-B9 scent seam
  (T005 extension or follow-on, orchestrator-recorded) and T021 for the property-suite
  close-out. The global `docs/TODO.md` ledger is reconciled by the orchestrator after each
  wave; this stage does not edit it.
- **Assumed delivered (prerequisites, per stage entry criteria):** C01 domain + config
  (T003/T004), scent model + lock (T005), orchestrator FSM + turn loop (T010), MCP
  transport + turn frames (T009), integrity core (T008).
