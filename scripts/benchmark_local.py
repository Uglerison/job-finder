"""Measure local startup, list and dashboard latency against E7 budgets."""

from __future__ import annotations

import ctypes
import json
import os
import tempfile
import time
from pathlib import Path
from urllib.request import urlopen

from job_finder.frontend import frontend_dist_path
from job_finder.launcher import LocalServer
from job_finder.main import create_app
from job_finder.settings import Settings

STARTUP_BUDGET_MS = 10_000
REQUEST_BUDGET_MS = 1_000
WORKING_SET_BUDGET_MB = 300


def _working_set_mb() -> float | None:
    if os.name != "nt":
        return None

    class MemoryCounters(ctypes.Structure):
        _fields_ = [
            ("cb", ctypes.c_ulong),
            ("page_fault_count", ctypes.c_ulong),
            ("peak_working_set_size", ctypes.c_size_t),
            ("working_set_size", ctypes.c_size_t),
            ("quota_peak_paged_pool_usage", ctypes.c_size_t),
            ("quota_paged_pool_usage", ctypes.c_size_t),
            ("quota_peak_non_paged_pool_usage", ctypes.c_size_t),
            ("quota_non_paged_pool_usage", ctypes.c_size_t),
            ("pagefile_usage", ctypes.c_size_t),
            ("peak_pagefile_usage", ctypes.c_size_t),
        ]

    counters = MemoryCounters()
    counters.cb = ctypes.sizeof(counters)
    process = ctypes.windll.kernel32.GetCurrentProcess()
    get_process_memory_info = ctypes.windll.psapi.GetProcessMemoryInfo
    get_process_memory_info.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(MemoryCounters),
        ctypes.c_ulong,
    ]
    get_process_memory_info.restype = ctypes.c_int
    succeeded = get_process_memory_info(
        process,
        ctypes.byref(counters),
        counters.cb,
    )
    if not succeeded:
        return None
    return counters.working_set_size / (1024 * 1024)


def _timed_request(url: str) -> float:
    started = time.perf_counter()
    with urlopen(url, timeout=2) as response:
        response.read()
    return (time.perf_counter() - started) * 1000


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="job-finder-benchmark-") as data_dir:
        settings = Settings(data_dir=Path(data_dir), environment="test", log_level="WARNING")
        server = LocalServer(
            create_app(settings, frontend_dist_dir=frontend_dist_path()),
            startup_timeout_seconds=STARTUP_BUDGET_MS / 1000,
        )
        started = time.perf_counter()
        server.start()
        startup_ms = (time.perf_counter() - started) * 1000
        try:
            health_ms = _timed_request(f"{server.url}/api/health")
            list_ms = _timed_request(f"{server.url}/api/jobs?limit=20")
            dashboard_ms = _timed_request(f"{server.url}/api/dashboard/summary?timezone=UTC")
            working_set_mb = _working_set_mb()
        finally:
            server.stop()

    metrics = {
        "startup_ms": round(startup_ms, 2),
        "health_ms": round(health_ms, 2),
        "list_ms": round(list_ms, 2),
        "dashboard_ms": round(dashboard_ms, 2),
        "working_set_mb": round(working_set_mb, 2) if working_set_mb is not None else None,
    }
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    if startup_ms > STARTUP_BUDGET_MS:
        raise SystemExit(f"Startup acima do orçamento: {startup_ms:.2f} ms")
    if max(health_ms, list_ms, dashboard_ms) > REQUEST_BUDGET_MS:
        raise SystemExit("Uma requisição local excedeu o orçamento de 1 s.")
    if working_set_mb is not None and working_set_mb > WORKING_SET_BUDGET_MB:
        raise SystemExit(f"Working set acima do orçamento: {working_set_mb:.2f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
