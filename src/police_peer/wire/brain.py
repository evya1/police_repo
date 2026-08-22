"""BrainDrivenEngine — the S3 glue swap: real PoliceBrain on POLICE sub-games.

Composes a ``SubgameSession`` (does NOT subclass ``StandInEngine``, and is not subclassed
by it — both adapters compose the shared session). On POLICE sub-games it resolves the
configured brain + belief, normalizes incoming scent at the wire boundary, and drives the
belief through the canonical ``apply_half_turn`` order once per accepted half-turn. A
barrier this peer places itself is excluded from the belief as soon as the domain
placement succeeds. THIEF sub-games keep the stand-in behaviour (SD-P7) via the same
``SubgameSession``, duplicated minimally rather than inherited.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from common.domain.scoring import Outcome, Role
from police_peer.wire.evidence import normalize_scent_field
from police_peer.wire.session import SubgameSession


@dataclass
class BrainDrivenEngine:
    """TurnEngine seam: real PoliceBrain on POLICE sub-games, stand-in on THIEF."""

    natural_role: Role
    board_size: int = 7
    seed: int = 0
    terms: dict | None = None
    config: dict | None = None

    _session: SubgameSession | None = None
    _brain: Any = None
    _belief: Any = None
    _last_field: dict[str, float] = field(default_factory=dict)
    _last_opponent_hint: str = ""
    _arena: str = "New York"

    def start_subgame(self, sub_game: int, role: Role, terms: dict | None = None) -> None:
        """Fresh session for every sub-game; on POLICE sub-games, fresh brain + belief too."""
        t = terms or self.terms or {}
        cfg = self.config or {}
        scent_model = str(cfg.get("scent_model")) if cfg.get("scent_model") else None
        self._session = SubgameSession(
            natural_role=self.natural_role, board_size=self.board_size, seed=self.seed,
            scent_model=scent_model,
        )
        self._session.start(sub_game, role, terms=t)
        self._brain = None
        self._belief = None
        self._last_field = {}
        self._last_opponent_hint = ""
        world = cfg.get("world")
        self._arena = str(world.get("map_area", "New York")) if isinstance(world, dict) else "New York"
        if role is Role.POLICE:
            from police_peer.belief import build_belief
            from police_peer.strategy import resolve_brain

            self._brain = resolve_brain(cfg, role)
            self._brain.reset(self._session.engine.position)
            self._belief = build_belief(self._session.engine.board, cfg, probe=None)

    def decide(self) -> dict:
        """Return a move dict. POLICE sub-games are brain-driven; THIEF keep the stand-in."""
        if self._session is None or self._session.engine is None:
            raise RuntimeError("start_subgame must be called before decide")

        if self._brain is not None:
            self._brain.note_evidence(self._last_field)
            decision = self._brain.decide(
                self._session.engine, self._belief, self._last_opponent_hint, self._arena,
            )
            # Barrier first: place barrier if decided, then apply move (FR-P2/FR-P4).
            if decision.barrier_cell is not None:
                # Domain placement first: it raises IllegalMoveError before it mutates, so a
                # refused placement must not leave the belief believing in a barrier that the
                # board never got. Only a placement that actually happened excludes the cell.
                self._session.engine.place_own_barrier(decision.barrier_cell)
                if self._belief is not None:
                    self._belief.exclude(decision.barrier_cell)
            self._session.apply_move(decision.action)
            return self._session.build_result(
                move=decision.action,
                hint=decision.hint,
                verdict=decision.verdict,
                fallback=decision.fallback,
                reasoning=decision.reasoning,
                prompt_text=decision.prompt_text,
                response_seconds=decision.response_seconds,
                barrier_cell=decision.barrier_cell,
            )

        # THIEF sub-games: stand-in behaviour (SD-P7), composed not inherited.
        legal_moves = self._session.engine.legal_moves()
        move = legal_moves[0] if legal_moves else "STAY"
        self._session.apply_move(move)
        return self._session.build_result(move=move, hint="I am here")

    def observe_opponent(self, message: dict) -> None:
        """Absorb an opponent's turn message; drive the belief through apply_half_turn exactly
        once per valid received half-turn, in the canonical pinned order.

        Semantic preflight FIRST: ``observe_barrier_and_claims`` is the only step that can
        still refuse a wire-valid turn (a quota-breaking or off-board barrier declaration).
        It raises before it mutates, so a refused turn leaves board, session and belief
        exactly as they were; the evidence order below runs only for an accepted turn.
        """
        if self._session is None or self._session.engine is None:
            return

        self._session.observe_barrier_and_claims(message)

        if self._belief is not None:
            from police_peer.belief.update import apply_half_turn

            board = self._session.engine.board
            self._last_field = normalize_scent_field(message.get("smell_grid"), board)
            self._last_opponent_hint = str(message.get("hint", ""))
            barrier = message.get("barrier_placed")
            barrier_cell = tuple(barrier) if isinstance(barrier, list) else barrier
            capture_landed = self._session.capture_landed_on_own_cell(message)
            apply_half_turn(
                self._belief,
                barrier=barrier_cell,
                field=self._last_field,
                hint=self._last_opponent_hint,
                arena=self._arena,
                own_cell=self._session.engine.position,
                capture_landed=capture_landed,
            )
        elif "smell_grid" in message:
            self._last_field = normalize_scent_field(
                message.get("smell_grid"), self._session.engine.board,
            )
        if "hint" in message:
            self._last_opponent_hint = str(message["hint"])

    def terminal(self) -> Outcome | None:
        if self._session is None:
            return None
        return self._session.terminal()

    def terminal_final(self) -> dict | None:
        """The game-ending final step owed after settling, or None.

        A thief that saw its own capture (rules 46/47 — a fact only the thief can
        see) owes a concession: a STAY naming its own final cell with caught=true.
        An answered claim or a survival claim already rode the last normal step, so
        only the invisible capture needs the extra sealed final. A police settling
        from the thief's final owes a plain sealed STAY.
        """
        if self._session is None or self._session.engine is None:
            return None
        eng = self._session.engine
        trail = self._session.trail
        smell_grid = trail.full_turn(eng.position) if trail is not None else {}
        if eng.role is Role.THIEF:
            if eng.self_captured() is None:
                return None
            self._session.apply_move("STAY")
            return {
                "move": "STAY",
                "hint": "",
                "state": eng.state_string(),
                "smell_grid": smell_grid,
                "claim_response": {"claim": [int(eng.position[0]), int(eng.position[1])],
                                   "caught": True},
            }
        if self.terminal() is None:
            return None
        self._session.apply_move("STAY")
        return {"move": "STAY", "hint": "", "state": eng.state_string(), "smell_grid": smell_grid}
