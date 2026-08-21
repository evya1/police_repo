"""Strategy protocol and deterministic baseline implementation."""

from __future__ import annotations

from typing import Any, Protocol


class Strategy(Protocol):
    """Replaceable boundary consuming redacted state and returning legal action."""

    def select_action(self, legal_moves: list[str], state_view: dict[str, Any]) -> str:
        """Given legal actions and local redacted state, return chosen action."""
        ...


class BaselineStrategy:
    """Simple deterministic legal baseline strategy."""

    def select_action(self, legal_moves: list[str], state_view: dict[str, Any] | None = None) -> str:
        """Pick the first legal move deterministically, or STAY if none available."""
        if not legal_moves:
            return "STAY"
        return legal_moves[0]
