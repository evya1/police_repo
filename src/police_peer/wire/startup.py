"""Startup validation of the raw shared config, before any peer exists.

Split out of ``sdk.py`` so that module stays the composition root itself. This is the one
place a raw config dict is checked for a supported schema version -- a peer that started on
an unrecognized schema would negotiate terms it cannot honour, so the refusal belongs here,
before construction, not at the first turn.
"""

from __future__ import annotations

from typing import Any

from common.config import ConfigError, validate_config

SUPPORTED_SCHEMA_VERSIONS = frozenset({"1.0", "1.1", "1.2"})


def validate_startup_config(raw_config: dict[str, Any]) -> None:
    """Validate raw config at startup, checking schema version and fields."""
    if not isinstance(raw_config, dict):
        raise ConfigError("Config must be a dictionary")
    version = raw_config.get("schema_version")
    if version is None:
        raise ConfigError("Missing required field 'schema_version'")
    if not isinstance(version, str) or version not in SUPPORTED_SCHEMA_VERSIONS:
        raise ConfigError(f"Unsupported schema_version: {version!r}")
    validate_config(raw_config)
