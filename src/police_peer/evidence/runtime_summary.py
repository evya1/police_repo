"""Coarse, secret-free hardware/runtime summary for the Step-0 declaration."""

from __future__ import annotations

import os
import platform
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class RuntimeSummary:
    """A coarse, secret-free hardware/runtime summary.

    Deliberately excludes hostname, username, filesystem paths, MAC/IP
    addresses, and environment variable values -- only platform facts that
    cannot identify the specific machine or leak local secrets.
    """

    os_name: str
    python_version: str
    cpu_count: int
    architecture: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "os_name": self.os_name,
            "python_version": self.python_version,
            "cpu_count": self.cpu_count,
            "architecture": self.architecture,
        }


def collect_runtime_summary() -> RuntimeSummary:
    """Collect the real, host-derived hardware/runtime summary."""
    return RuntimeSummary(
        os_name=platform.system(),
        python_version=platform.python_version(),
        cpu_count=os.cpu_count() or 0,
        architecture=platform.machine(),
    )
