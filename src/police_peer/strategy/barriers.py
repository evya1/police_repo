"""Barrier decision — the pure where_place_barrier pipeline.

Role-specific (police_repo only). Pure functions, no engine mutation.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Mapping

from common.domain.board import Board, Cell
from common.domain.scoring import Role

from .base import BeliefGrid


def where_place_barrier(
    state, belief: BeliefGrid, cfg: Mapping[str, object]
) -> Cell | None:
    """Decide WHETHER to place a barrier this turn and WHERE (from
    state.barrier_targets()). Returns the target cell, or None (= move
    instead). Pure, deterministic. Pipeline (PRD FR-P2, fixed order):

    1. Guards, else None: state.role is Role.POLICE;
       state.barriers_placed < state.barriers_max;
       candidates = state.barrier_targets() non-empty.
    2. peak = belief.most_likely().
    3. Per candidate c (barrier_targets() order — own cell first, then
       in-bounds unblocked orthogonal neighbours in N, S, W, E order):
           mass = belief.prob(c)
           cut  = cut_value(state, c, peak)
           skip if mass < cfg["barrier_mass_floor"] and cut == 0   # no value
           skip if the Police->peak BFS distance worsens by more
                than cfg["route_slack"] when c is added            # self-route
           score = cfg["w_mass"] * mass + cfg["w_cut"] * (cut / before)
           skip (reserve) if remaining <= cfg["barrier_reserve"]
                and score < cfg["strong_threshold"]
           keep the best (strictly greater; first candidate wins ties)
    4. Return the best iff its score >= cfg["barrier_score_threshold"],
       else None.
    """
    # Guard 1: only the Police places barriers.
    if state.role is not Role.POLICE:
        return None
    # Guard 2: quota check.
    if state.barriers_placed >= state.barriers_max:
        return None
    # Guard 3: candidates non-empty.
    candidates = state.barrier_targets()
    if not candidates:
        return None

    peak = belief.most_likely()
    remaining = state.barriers_max - state.barriers_placed
    floor = float(cfg.get("barrier_mass_floor", 0.05))
    w_mass = float(cfg.get("w_mass", 1.0))
    w_cut = float(cfg.get("w_cut", 0.5))
    slack = int(cfg.get("route_slack", 1))
    reserve = int(cfg.get("barrier_reserve", 3))
    strong = float(cfg.get("strong_threshold", 0.8))
    threshold = float(cfg.get("barrier_score_threshold", 0.3))

    # Baseline BFS distance from Police position to peak (with current barriers).
    police_pos = state.position
    current_barriers = frozenset(state.barriers)
    baseline_dist = _bfs_distance(state.board, police_pos, peak, current_barriers)

    best_candidate: Cell | None = None
    best_score = -1.0

    for c in candidates:
        mass = belief.prob(c)
        cut = cut_value(state, c, peak)

        # Skip: no value (low mass AND zero cut).
        if mass < floor and cut == 0:
            continue

        # Skip: self-route guard — don't worsen our chase by more than slack.
        new_barriers = current_barriers | {c}
        new_dist = _bfs_distance(state.board, police_pos, peak, new_barriers)
        if new_dist > baseline_dist + slack:
            continue

        # Compute score.
        before = cut + int(belief.prob(peak) > 0)  # before = cut + after; after = before - cut
        # More precisely: before = _reachable from peak with current barriers.
        before = _reachable(state.board, peak, current_barriers)
        assert before >= 1, "belief excludes barrier cells (FR-B4), so reachable >= 1"
        score = w_mass * mass + w_cut * (cut / before)

        # Skip (reserve): save last barriers for the late game.
        if remaining <= reserve and score < strong:
            continue

        # Keep if strictly greater (first candidate wins ties).
        if score > best_score:
            best_score = score
            best_candidate = c

    if best_candidate is not None and best_score >= threshold:
        return best_candidate
    return None


def cut_value(state, c: Cell, peak: Cell) -> int:
    """Region collapse from adding barrier c: before - after, where
    before/after are _reachable sizes from `peak` (orthogonal, barriers
    impassable). If c == peak: returns `before` — full region collapse plus
    the rule-46 capture gamble (GAME-010): a barrier on the Thief's cell is a
    capture the Thief must honestly acknowledge. `before` is >= 1 because the
    belief excludes barrier cells (belief FR-B4); a defensive assert pins it.
    """
    board: Board = state.board
    current_barriers = frozenset(state.barriers)
    if c == peak:
        # Full region collapse: barrier on the peak eliminates the entire reachable region.
        before = _reachable(board, peak, current_barriers)
        assert before >= 1, "belief excludes barrier cells (FR-B4), so reachable >= 1"
        return before

    before = _reachable(board, peak, current_barriers)
    new_barriers = current_barriers | {c}
    after = _reachable(board, peak, new_barriers)
    return before - after


def _reachable(board: Board, from_cell: Cell, barriers: frozenset[Cell]) -> int:
    """BFS flood-fill size from `from_cell`: orthogonal neighbours, in-bounds,
    barriers impassable. The only graph helper in the module; pure O(cells).
    """
    if not board.in_bounds(from_cell):
        return 0
    visited: set[Cell] = {from_cell}
    queue = deque([from_cell])
    count = 1
    while queue:
        cell = queue.popleft()
        for nb in board.neighbours(cell):
            if nb in visited or nb in barriers:
                continue
            visited.add(nb)
            queue.append(nb)
            count += 1
    return count


def _bfs_distance(board: Board, start: Cell, end: Cell, barriers: frozenset[Cell]) -> float:
    """BFS shortest-path distance from start to end. Returns inf if unreachable."""
    if start == end:
        return 0.0
    visited: set[Cell] = {start}
    queue = deque([(start, 0)])
    while queue:
        cell, dist = queue.popleft()
        for nb in board.neighbours(cell):
            if nb == end:
                return dist + 1
            if nb in visited or nb in barriers:
                continue
            visited.add(nb)
            queue.append((nb, dist + 1))
    return float("inf")
