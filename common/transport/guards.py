"""Shared-layer guards: source-scan for FR-39 compliance.

STUB — to be replaced by the real implementation in ST-14 (T009/T022).
"""

from __future__ import annotations

from collections.abc import Iterable


def scan_shared_layer(paths: Iterable[str]) -> list[str]:
    """Scan source files for guard violations. Return list of violations.

    FR-39: no network import outside mcp_server/mcp_client/probes/readiness;
    no fastmcp outside the two transport modules; no module-level mutable state
    in common/transport/; no role-code import into common/; one canonical hash path.
    """
    # STUB: placeholder
    return []


def preflight_check(paths: Iterable[str]) -> bool:
    """Run the guard scan. Return True if clean."""
    # STUB: placeholder
    return True
