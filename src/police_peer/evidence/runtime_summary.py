"""Coarse, secret-free hardware/runtime summary for the Step-0 declaration."""

from __future__ import annotations

import os
import platform
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class RuntimeSummary:
    """A coarse, secret-free hardware/runtime summary.

    Deliberately excludes hostname, username, filesystem paths, MAC/IP
    addresses, and environment variable values -- only platform facts that
    cannot identify the specific machine or leak local secrets.
    """

    cpu_type: str
    cpu_freq_mhz: float | None
    cpu_cores: int
    ram_gb: float | None
    gpu_model: str | None
    vram_gb: float | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "cpu_type": self.cpu_type,
            "cpu_freq_mhz": self.cpu_freq_mhz,
            "cpu_cores": self.cpu_cores,
            "ram_gb": self.ram_gb,
            "gpu_model": self.gpu_model,
            "vram_gb": self.vram_gb,
        }


def _cpu_info(label: str) -> str | None:
    """Read one non-secret Linux CPU fact when procfs is available."""
    try:
        for line in Path("/proc/cpuinfo").read_text(encoding="utf-8").splitlines():
            key, separator, value = line.partition(":")
            if separator and key.strip() == label:
                return value.strip() or None
    except OSError:
        return None
    return None


def _ram_gb() -> float | None:
    try:
        total = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
    except (AttributeError, OSError, TypeError, ValueError):
        return None
    return round(total / (1024 ** 3), 2)


def collect_runtime_summary() -> RuntimeSummary:
    """Collect the real, host-derived hardware/runtime summary."""
    raw_frequency = _cpu_info("cpu MHz")
    try:
        frequency = float(raw_frequency) if raw_frequency is not None else None
    except ValueError:
        frequency = None
    return RuntimeSummary(
        cpu_type=_cpu_info("model name") or platform.processor() or platform.machine(),
        cpu_freq_mhz=frequency,
        cpu_cores=os.cpu_count() or 0,
        ram_gb=_ram_gb(),
        gpu_model=None,
        vram_gb=None,
    )
