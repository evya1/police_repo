"""Purity tests: belief module imports no strategy, transport, or opponent-truth code.

Covers TC-B12, FR-B7.
"""

from __future__ import annotations


class TestImportPurity:
    """belief/ imports no strategy, transport, or opponent-truth code."""

    def test_belief_grid_no_strategy_imports(self) -> None:
        import police_peer.belief.grid as grid_mod

        imported_modules = set()
        for name in dir(grid_mod):
            obj = getattr(grid_mod, name)
            if hasattr(obj, "__module__"):
                imported_modules.add(obj.__module__)
        for mod in imported_modules:
            assert "strategy" not in mod, f"grid.py imports strategy via {mod}"
            assert "transport" not in mod, f"grid.py imports transport via {mod}"
            assert "scent.profiles" not in mod, f"grid.py imports scent.profiles via {mod}"

    def test_belief_update_no_strategy_imports(self) -> None:
        import police_peer.belief.update as update_mod

        imported_modules = set()
        for name in dir(update_mod):
            obj = getattr(update_mod, name)
            if hasattr(obj, "__module__"):
                imported_modules.add(obj.__module__)
        for mod in imported_modules:
            assert "strategy" not in mod, f"update.py imports strategy via {mod}"
            assert "transport" not in mod, f"update.py imports transport via {mod}"
            assert "scent.profiles" not in mod, f"update.py imports scent.profiles via {mod}"

    def test_belief_probe_no_strategy_imports(self) -> None:
        import police_peer.belief.probe as probe_mod

        imported_modules = set()
        for name in dir(probe_mod):
            obj = getattr(probe_mod, name)
            if hasattr(obj, "__module__"):
                imported_modules.add(obj.__module__)
        for mod in imported_modules:
            assert "strategy" not in mod, f"probe.py imports strategy via {mod}"
            assert "transport" not in mod, f"probe.py imports transport via {mod}"
            assert "scent.profiles" not in mod, f"probe.py imports scent.profiles via {mod}"

    def test_belief_hints_no_strategy_imports(self) -> None:
        import police_peer.belief.hints as hints_mod

        imported_modules = set()
        for name in dir(hints_mod):
            obj = getattr(hints_mod, name)
            if hasattr(obj, "__module__"):
                imported_modules.add(obj.__module__)
        for mod in imported_modules:
            assert "strategy" not in mod, f"hints.py imports strategy via {mod}"
            assert "transport" not in mod, f"hints.py imports transport via {mod}"

    def test_belief_init_no_strategy_imports(self) -> None:
        import police_peer.belief as belief_pkg

        imported_modules = set()
        for name in dir(belief_pkg):
            obj = getattr(belief_pkg, name)
            if hasattr(obj, "__module__"):
                imported_modules.add(obj.__module__)
        for mod in imported_modules:
            assert "strategy" not in mod, f"__init__.py imports strategy via {mod}"
            assert "transport" not in mod, f"__init__.py imports transport via {mod}"
            assert "scent.profiles" not in mod, f"__init__.py imports scent.profiles via {mod}"
