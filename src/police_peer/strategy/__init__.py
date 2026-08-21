"""Strategy package — shared core + Police-specific policy.

Public re-exports. The shared-core files are identical in both role
repositories modulo package import path and the role constant.
"""

from __future__ import annotations

from .barriers import where_place_barrier
from .base import BrainBase
from .decision import Decision
from .hints import HintWriter, TextProvider
from .inject import resolve_brain, resolve_brain_cls
from .police import PoliceBrain

__all__ = [
    "BrainBase",
    "Decision",
    "HintWriter",
    "TextProvider",
    "PoliceBrain",
    "where_place_barrier",
    "resolve_brain",
    "resolve_brain_cls",
]
