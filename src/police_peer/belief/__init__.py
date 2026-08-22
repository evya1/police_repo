"""Belief board — opponent-location inference under partial observation.

Builds a normalized belief distribution over an NxN board, updated from
opponent scent (two calibrated forms) and deterministic hint evidence.
Private-key reads only; fail-fast on unknown update_form.
"""

from __future__ import annotations

from collections.abc import Mapping

from common.domain.board import Board

from .grid import BeliefGrid
from .probe import EmissionProbe


def build_belief(
    board: Board,
    cfg: Mapping[str, object],
    probe: EmissionProbe | None,
) -> BeliefGrid:
    """Read private [belief] keys off the resolved config mapping.

    Unknown ``update_form`` -> ``ValueError``.
    ``kernel_bayes_v1`` without a probe -> ``ValueError``.
    """
    belief_cfg = dict(cfg.get("belief", {}) or {})

    trust = float(belief_cfg.get("smell_trust_weight", 4.0))
    update_form = str(belief_cfg.get("update_form", "trust_v1"))
    hint_reliability = float(belief_cfg.get("hint_reliability", 0.25))

    if update_form not in ("trust_v1", "kernel_bayes_v1"):
        raise ValueError(f"unknown update_form {update_form!r}")

    if update_form == "kernel_bayes_v1" and probe is None:
        raise ValueError("kernel_bayes_v1 requires an EmissionProbe")

    return BeliefGrid(
        board=board,
        trust=trust,
        update_form=update_form,
        hint_reliability=hint_reliability,
        probe=probe,
    )
