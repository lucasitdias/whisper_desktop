"""Telemetria leve do processo, sem importar PyTorch nem psutil na interface."""

from __future__ import annotations

import ctypes
import os
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ResourceSnapshot:
    cpu_percent: float
    ram_mb: float


def current_process_rss_bytes() -> int:
    """Retorna a memória residente/working set do processo atual."""
    if sys.platform.startswith("win"):
        from ctypes import wintypes

        class ProcessMemoryCounters(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        counters = ProcessMemoryCounters()
        counters.cb = ctypes.sizeof(counters)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        psapi.GetProcessMemoryInfo.argtypes = [
            wintypes.HANDLE,
            ctypes.c_void_p,
            wintypes.DWORD,
        ]
        psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
        kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        psapi.GetProcessMemoryInfo.argtypes = [
            wintypes.HANDLE,
            ctypes.c_void_p,
            wintypes.DWORD,
        ]
        psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
        if not psapi.GetProcessMemoryInfo(
            kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb
        ):
            raise OSError(ctypes.get_last_error(), "GetProcessMemoryInfo falhou")
        return int(counters.WorkingSetSize)

    statm = "/proc/self/statm"
    if os.path.isfile(statm):
        with open(statm, encoding="ascii") as handle:  # noqa: PTH123
            resident_pages = int(handle.read().split()[1])
        return resident_pages * int(os.sysconf("SC_PAGE_SIZE"))

    import resource

    maximum_rss = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return maximum_rss if sys.platform == "darwin" else maximum_rss * 1024


class ProcessResourceSampler:
    """Amostra CPU e RAM do aplicativo com custo baixo e comportamento multiplataforma."""

    def __init__(
        self,
        *,
        clock: Callable[[], float] = time.monotonic,
        process_clock: Callable[[], float] = time.process_time,
        rss_reader: Callable[[], int] = current_process_rss_bytes,
        processor_count: int | None = None,
    ) -> None:
        self._clock = clock
        self._process_clock = process_clock
        self._rss_reader = rss_reader
        self._processor_count = max(1, processor_count or os.cpu_count() or 1)
        self._last_wall = self._clock()
        self._last_cpu = self._process_clock()

    def sample(self) -> ResourceSnapshot:
        wall = self._clock()
        cpu = self._process_clock()
        wall_delta = max(0.0, wall - self._last_wall)
        cpu_delta = max(0.0, cpu - self._last_cpu)
        self._last_wall = wall
        self._last_cpu = cpu
        cpu_percent = (
            min(100.0, cpu_delta / wall_delta * 100.0 / self._processor_count)
            if wall_delta > 0
            else 0.0
        )
        try:
            ram_mb = max(0, self._rss_reader()) / (1024 * 1024)
        except (OSError, ValueError, IndexError):
            ram_mb = 0.0
        return ResourceSnapshot(cpu_percent=cpu_percent, ram_mb=ram_mb)
