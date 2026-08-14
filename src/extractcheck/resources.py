"""Allowlisted local resource readings; unsupported metrics stay explicit."""
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import sys

try:
    import resource as _resource
except ModuleNotFoundError:  # Windows does not provide the Unix resource module.
    _resource = None


@dataclass(frozen=True)
class ResourceSample:
    rss_bytes: int | None
    free_memory_ratio: float | None
    supported: bool
    unsupported_codes: tuple[str, ...]


def _linux_rss() -> int | None:
    try:
        for line in Path(f"/proc/{os.getpid()}/status").read_text(encoding="ascii").splitlines():
            if line.startswith("VmRSS:"):
                return int(line.split()[1]) * 1024
    except (OSError, ValueError, IndexError):
        return None
    return None


def _free_ratio() -> float | None:
    if sys.platform.startswith("linux"):
        try:
            values: dict[str, int] = {}
            for line in Path("/proc/meminfo").read_text(encoding="ascii").splitlines():
                key, value = line.split(":", 1)
                values[key] = int(value.split()[0]) * 1024
            return values["MemAvailable"] / values["MemTotal"]
        except (OSError, ValueError, KeyError, IndexError):
            return None
    return None


def sample_resources() -> ResourceSample:
    if sys.platform.startswith("linux"):
        rss = _linux_rss()
    elif sys.platform == "darwin" and _resource is not None:
        rss = int(_resource.getrusage(_resource.RUSAGE_SELF).ru_maxrss)
    else:
        rss = None
    ratio = _free_ratio()
    unsupported: list[str] = []
    if rss is None:
        unsupported.append("rss_unsupported")
    if ratio is None:
        unsupported.append("free_memory_ratio_unsupported")
    return ResourceSample(rss, ratio, not unsupported, tuple(unsupported))
