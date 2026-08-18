"""Purity tests: the scent module imports no transport, strategy, belief, or domain code.

Covers T005 L88.
"""

from __future__ import annotations


class TestImportPurity:
    """The scent module and its submodules import no transport, strategy, belief, or domain code."""

    def test_scent_model_no_transport_imports(self) -> None:
        """model.py should not import transport, negotiate, or any wire code."""
        import police_peer.scent.model as model_mod
        imported_modules = set()
        for name in dir(model_mod):
            obj = getattr(model_mod, name)
            if hasattr(obj, "__module__"):
                imported_modules.add(obj.__module__)
        for mod in imported_modules:
            assert "transport" not in mod, f"model.py imports transport via {mod}"
            assert "negotiate" not in mod, f"model.py imports negotiate via {mod}"
            assert "policy" not in mod, f"model.py imports policy via {mod}"
            assert "strategy" not in mod, f"model.py imports strategy via {mod}"
            assert "belief" not in mod, f"model.py imports belief via {mod}"

    def test_scent_lock_no_transport_imports(self) -> None:
        """lock.py should not import transport, negotiate, or any wire code."""
        import police_peer.scent.lock as lock_mod
        imported_modules = set()
        for name in dir(lock_mod):
            obj = getattr(lock_mod, name)
            if hasattr(obj, "__module__"):
                imported_modules.add(obj.__module__)
        for mod in imported_modules:
            assert "transport" not in mod, f"lock.py imports transport via {mod}"
            assert "negotiate" not in mod, f"lock.py imports negotiate via {mod}"
            assert "policy" not in mod, f"lock.py imports policy via {mod}"
            assert "strategy" not in mod, f"lock.py imports strategy via {mod}"
            assert "belief" not in mod, f"lock.py imports belief via {mod}"

    def test_scent_profiles_no_transport_imports(self) -> None:
        """Profile modules should not import transport, negotiate, or any wire code."""
        from police_peer.scent.profiles import multiplicative_book_v1, subtractive_chebyshev_v1
        for mod in (subtractive_chebyshev_v1, multiplicative_book_v1):
            imported_modules = set()
            for name in dir(mod):
                obj = getattr(mod, name)
                if hasattr(obj, "__module__"):
                    imported_modules.add(obj.__module__)
            for imp in imported_modules:
                assert "transport" not in imp, f"{mod.__name__} imports transport via {imp}"
                assert "negotiate" not in imp, f"{mod.__name__} imports negotiate via {imp}"
                assert "policy" not in imp, f"{mod.__name__} imports policy via {imp}"
                assert "strategy" not in imp, f"{mod.__name__} imports strategy via {imp}"
                assert "belief" not in imp, f"{mod.__name__} imports belief via {imp}"

    def test_scent_init_no_transport_imports(self) -> None:
        """__init__.py should not import transport, negotiate, or any wire code."""
        import police_peer.scent as scent_pkg
        imported_modules = set()
        for name in dir(scent_pkg):
            obj = getattr(scent_pkg, name)
            if hasattr(obj, "__module__"):
                imported_modules.add(obj.__module__)
        for mod in imported_modules:
            assert "transport" not in mod, f"__init__.py imports transport via {mod}"
            assert "negotiate" not in mod, f"__init__.py imports negotiate via {mod}"
            assert "policy" not in mod, f"__init__.py imports policy via {mod}"
            assert "strategy" not in mod, f"__init__.py imports strategy via {mod}"
            assert "belief" not in mod, f"__init__.py imports belief via {mod}"
