"""One installed-package module identity for the strategy core.

Regression guard for the two-module split (importing the package through the
repository-relative `src.` path instead of the installed `police_peer` path):
loading one source file under two module names makes two distinct class objects,
so an isinstance/identity check across the production/test boundary silently
fails and a source-inspection test can inspect a module production never uses.
Tests must import exactly the modules production imports.
"""

from __future__ import annotations

import sys

from common.domain.scoring import Role
from police_peer.strategy import Decision, PoliceBrain
from police_peer.strategy.base import BrainBase
from police_peer.strategy.decision import Decision as DecisionFromModule
from police_peer.strategy.police import PoliceBrain as PoliceBrainFromModule
from police_peer.wire import BrainDrivenEngine

_TERMS = {
    "board_size": 7, "smell_grid_size": 5, "decay_per_step": 0.1, "emit_intensity": 0.9,
    "min_center_intensity": 0.5, "max_steps": 35, "barriers_max": 14,
    "thief_start": [3, 3], "cop_start": [0, 0],
}


def test_no_duplicate_path_prefixed_module_is_loaded() -> None:
    """Nothing in the suite may import a package through the repo-relative path."""
    duplicates = [name for name in sys.modules if name.split(".")[0] == "src"]
    assert duplicates == []


def test_package_reexports_are_the_same_class_objects() -> None:
    assert PoliceBrain is PoliceBrainFromModule
    assert Decision is DecisionFromModule
    assert PoliceBrain.__module__ == "police_peer.strategy.police"
    assert Decision.__module__ == "police_peer.strategy.decision"


def test_production_composition_builds_the_test_imported_classes() -> None:
    """The brain the production composition root builds IS this module's PoliceBrain."""
    engine = BrainDrivenEngine(Role.POLICE, board_size=7, seed=0, config={})
    engine.start_subgame(1, Role.POLICE, terms=_TERMS)
    brain = engine._brain
    assert type(brain) is PoliceBrain
    assert isinstance(brain, BrainBase)

    decision = brain.decide(engine._session.engine, engine._belief, "", "New York")
    assert type(decision) is Decision
