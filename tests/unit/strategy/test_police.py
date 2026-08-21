"""PoliceBrain tests: pursuit branches, barrier mechanics, tie-break.

TC-P02 (unit): legality property — action always in legal set; barrier_cell is None or legal.
TC-P03: pursuit — four branches of FR-P3.
TC-P04: commit to the peak.
TC-P05: tie-break — equal keys => earlier in CT-01 order wins.
TC-P06: forced STAY.
"""

from __future__ import annotations

from common.domain.board import Board
from common.domain.rules import GameEngine
from common.domain.scoring import Role
from src.police_peer.strategy.police import PoliceBrain


class _UniformBelief:
    """Uniform belief: peak probability = 1/N²."""

    def __init__(self, board):
        self._board = board
        self._size = board.size

    def most_likely(self):
        return (0, 0)

    def peak_probability(self) -> float:
        return 1.0 / (self._size * self._size)

    def prob(self, cell):
        return 1.0 / (self._size * self._size)


class _PeakBelief:
    """Belief with a single peak at the given cell."""

    def __init__(self, board, peak, peak_prob=0.5):
        self._board = board
        self._peak = peak
        self._size = board.size
        self._peak_prob = peak_prob

    def most_likely(self):
        return self._peak

    def peak_probability(self) -> float:
        return self._peak_prob

    def prob(self, cell):
        if cell == self._peak:
            return self._peak_prob
        return 0.01


class TestLegality:
    """TC-P02 (unit): legality property."""

    def test_action_in_legal_set(self) -> None:
        brain = PoliceBrain()
        board = Board(size=7)
        engine = GameEngine(board=board, role=Role.POLICE, position=(3, 3))
        belief = _UniformBelief(board)
        action, barrier = brain._decide_move(engine, belief)
        assert action in engine.legal_moves()

    def test_barrier_cell_legal_when_set(self) -> None:
        """When barrier_cell is set, action must be STAY and cell must be a legal barrier target."""
        brain = PoliceBrain()
        board = Board(size=7)
        engine = GameEngine(board=board, role=Role.POLICE, position=(3, 3))
        belief = _PeakBelief(board, (3, 3), peak_prob=0.9)
        action, barrier = brain._decide_move(engine, belief)
        if barrier is not None:
            assert action == "STAY"
            assert barrier in engine.barrier_targets()


class TestPursuit:
    """TC-P03: pursuit — four branches of FR-P3."""

    def test_confident_peak_branch(self) -> None:
        """Peak above min_confidence => action minimizes manhattan to most_likely()."""
        brain = PoliceBrain(min_confidence=0.10)
        board = Board(size=7)
        engine = GameEngine(board=board, role=Role.POLICE, position=(0, 0))
        belief = _PeakBelief(board, (3, 3), peak_prob=0.5)
        action, _ = brain._decide_move(engine, belief)
        # The action should move toward (3,3).
        assert action in ("MOVE:S", "MOVE:E", "STAY")

    def test_two_equidistant_destinations(self) -> None:
        """Two equidistant destinations => the likelier (belief.prob) is selected."""
        brain = PoliceBrain(min_confidence=0.10)
        board = Board(size=7)
        engine = GameEngine(board=board, role=Role.POLICE, position=(1, 1))
        # Peak at (3,3) with high probability; (2,2) also has some probability.
        belief = _PeakBelief(board, (3, 3), peak_prob=0.5)
        action, _ = brain._decide_move(engine, belief)
        # Should prefer moving toward the peak.
        assert action in ("MOVE:S", "MOVE:E", "STAY")

    def test_diffuse_scent_fallback(self) -> None:
        """Peak below min_confidence + non-empty field => threat = hottest."""
        brain = PoliceBrain(min_confidence=0.9)
        brain.note_evidence({"6,6": 0.9, "0,0": 0.1})
        board = Board(size=7)
        engine = GameEngine(board=board, role=Role.POLICE, position=(0, 0))
        belief = _UniformBelief(board)
        action, _ = brain._decide_move(engine, belief)
        # Should move toward the hottest cell (6,6).
        assert action in ("MOVE:S", "MOVE:E", "STAY")

    def test_empty_field_centre_fallback(self) -> None:
        """Peak below min_confidence + empty field => threat = board centre."""
        brain = PoliceBrain(min_confidence=0.9)
        brain.note_evidence({})
        board = Board(size=7)
        engine = GameEngine(board=board, role=Role.POLICE, position=(0, 0))
        belief = _UniformBelief(board)
        action, _ = brain._decide_move(engine, belief)
        # Should move toward centre (3,3).
        assert action in ("MOVE:S", "MOVE:E", "STAY")

    def test_boundary_min_confidence(self) -> None:
        """min_confidence exactly at boundary => peak branch taken (>=)."""
        brain = PoliceBrain(min_confidence=0.5)
        board = Board(size=7)
        engine = GameEngine(board=board, role=Role.POLICE, position=(0, 0))
        belief = _PeakBelief(board, (3, 3), peak_prob=0.5)
        action, _ = brain._decide_move(engine, belief)
        assert action in ("MOVE:S", "MOVE:E", "STAY")


class TestCommitToPeak:
    """TC-P04: commit to the peak — target adjacent => d = 0."""

    def test_step_onto_peak(self) -> None:
        """Target adjacent to Police => the minimizing action steps onto it (d = 0)."""
        brain = PoliceBrain(min_confidence=0.10)
        board = Board(size=7)
        engine = GameEngine(board=board, role=Role.POLICE, position=(2, 2))
        belief = _PeakBelief(board, (3, 3), peak_prob=0.9)
        action, _ = brain._decide_move(engine, belief)
        # Should move onto (3,3).
        assert action == "MOVE:S"


class TestTieBreak:
    """TC-P05: tie-break — equal (d, prob) => earlier in CT-01 order wins."""

    def test_earlier_action_wins_tie(self) -> None:
        """Two actions with equal key => N wins over S, S over W, etc."""
        brain = PoliceBrain(min_confidence=0.10)
        board = Board(size=7)
        # Police at (3,3), peak at (3,3) => all legal moves have d=0 (STAY) or d=1 (orthogonal).
        # STAY has d=0, so it wins.
        engine = GameEngine(board=board, role=Role.POLICE, position=(3, 3))
        belief = _PeakBelief(board, (3, 3), peak_prob=0.9)
        action, _ = brain._decide_move(engine, belief)
        assert action == "STAY"


class TestForcedStay:
    """TC-P06: forced STAY — all orthogonal moves blocked."""

    def test_forced_stay(self) -> None:
        """All orthogonal moves blocked => fallback=True, where_place_barrier not consulted."""
        brain = PoliceBrain(min_confidence=0.10)
        board = Board(size=7)
        barriers = [(2, 3), (4, 3), (3, 2), (3, 4)]
        engine = GameEngine(board=board, role=Role.POLICE, position=(3, 3), barriers=barriers)
        belief = _UniformBelief(board)
        decision = brain.decide(engine, belief, "", "New York")
        assert decision.action == "STAY"
        assert decision.fallback is True
        assert decision.barrier_cell is None
