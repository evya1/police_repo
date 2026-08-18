"""Tests for the transport module imports.

Verify that common.transport can be imported without importing fastmcp.
"""

from __future__ import annotations


def test_import_transport_without_fastmcp() -> None:
    """TC-02: importing common.transport must not pull in fastmcp."""
    import sys

    # Remove fastmcp from sys.modules if it was already imported
    fastmcp_modules = [k for k in sys.modules if k.startswith("fastmcp")]
    for mod in fastmcp_modules:
        del sys.modules[mod]

    # Now import the transport module
    import common.transport  # noqa: F401
    import common.transport.loopback  # noqa: F401
    import common.transport.series  # noqa: F401
    import common.transport.transport  # noqa: F401

    # Verify fastmcp was not imported
    fastmcp_after = [k for k in sys.modules if k.startswith("fastmcp")]
    assert fastmcp_after == [], f"fastmcp modules were imported: {fastmcp_after}"
