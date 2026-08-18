"""Scent model interface — two registered profiles behind one small common API.

There is no float maths in this module on purpose. Both registered models live in
``profiles/`` and are checked against ``vectors/pheromone.json`` and
``vectors/scent_book_v3.json``; re-deriving either here would create a second implementation
that could drift from the fixtures without anything noticing.

Two models, both selectable, because real pairings lock either one:

* ``subtractive_chebyshev_v1`` — the reference's: linear Chebyshev falloff, subtractive decay,
  rounded to 3 places, and **transmitted** on the wire. The default, because it is what
  ``wire_shape: reference-v3`` carries.
* ``multiplicative_book_v1`` — the book's own: a verbatim 5x5 figure-4 kernel, multiplicative
  decay, no rounding, once per full turn.

Note the asymmetry between the profiles: the book model's registration says ``transmitted: false`` —
each side is meant to *recompute* the rival's field rather than receive it. Running it under
``reference-v3`` therefore means "book physics, still transmitted". That is a real combination a
pair may lock, so it is allowed here and declared in the handshake rather than refused locally.
"""

from __future__ import annotations

from common.domain.board import Cell
from police_peer.scent.profiles.multiplicative_book_v1 import book_full_turn
from police_peer.scent.profiles.subtractive_chebyshev_v1 import (
    smell_decay,
    smell_emit,
)

REFERENCE_MODEL = "subtractive_chebyshev_v1"
BOOK_MODEL = "multiplicative_book_v1"
MODELS = (REFERENCE_MODEL, BOOK_MODEL)
DEFAULT_MODEL = REFERENCE_MODEL


class Trail:
    """One agent's own scent field, in the wire form ``{"r,c": intensity}``."""

    def __init__(self, model: str, board_size: int, *, field_size: int = 5,
                 emit_intensity: float = 0.9, decay_per_step: float = 0.1,
                 min_center_intensity: float = 0.5) -> None:
        if model not in MODELS:
            raise ValueError(
                f"unknown scent model {model!r}; expected one of {MODELS}"
            )
        self.model = model
        self.board_size = board_size
        self.field_size = field_size
        self.emit_intensity = emit_intensity
        self.decay_per_step = decay_per_step
        self.min_center_intensity = min_center_intensity
        self.field: dict[str, float] = {}

    def full_turn(self, center: Cell) -> dict[str, float]:
        """Advance one FULL turn — after both agents have moved, which is the book's cadence.

        The two models differ in every detail of how, which is exactly why they are registered
        separately and why a pair locks one before playing.
        """
        if self.model == BOOK_MODEL:
            self.field = book_full_turn(
                self.field, list(center), self.decay_per_step,
                self.emit_intensity, self.board_size,
            )
            return self.snapshot()

        # reference model: emit, merge by max, then decay — deposit-then-decay, rounded.
        if self.emit_intensity >= self.min_center_intensity:
            emitted = smell_emit(
                list(center), self.emit_intensity, self.field_size, self.board_size,
            )
            for key, value in emitted.items():
                if value > self.field.get(key, 0.0):
                    self.field[key] = value
        self.field = {
            k: v for k, v in smell_decay(self.field, self.decay_per_step).items()
            if v > 0.0
        }
        return self.snapshot()

    def snapshot(self) -> dict[str, float]:
        """What crosses the wire: only cells that still carry something."""
        return dict(self.field)


def hottest(field: dict[str, float]) -> Cell | None:
    """The strongest cell in an observed field, ties broken lexicographically by (row, col).

    Deterministic tie-breaking matters more than it looks: it is what lets a seeded self-play run
    reproduce byte-for-byte, which is what makes the golden test in CI meaningful.
    """
    if not field:
        return None
    best = max(
        field.items(),
        key=lambda kv: (kv[1], -_cell(kv[0])[0], -_cell(kv[0])[1]),
    )
    return _cell(best[0])


def make_trail(board_size: int, model: str | None = None,
               **params) -> Trail:
    """Factory: build a Trail with the given model (defaulting to DEFAULT_MODEL).

    No profile code hardcodes a model; the seam here is the explicit parameter plus the
    DEFAULT_MODEL constant. Swapping in a config read later must not touch the profiles.
    """
    if model is None:
        model = DEFAULT_MODEL
    return Trail(model, board_size, **params)


def _cell(key: str) -> Cell:
    r, c = key.split(",")
    return (int(r), int(c))
