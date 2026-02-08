from __future__ import annotations

import platform
import shutil
import subprocess
from typing import Any

import psutil


def _safe_float(value: float) -> float:
    return round(float(value), 2)


def _get_gpu_info() -> dict[str, Any] | None:
    if not shutil.which("nvidia-smi"):
        return None
    try:
        out = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total,memory.used,utilization.gpu",
                "--format=csv,noheader,nounits",
            ],
            text=True,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None
    if not out:
        return None
    first = out.splitlines()[0]
    parts = [p.strip() for p in first.split(",")]
    if len(parts) < 4:
        return None
    return {
        "name": parts[0],
        "memory_total_mb": int(parts[1]),
        "memory_used_mb": int(parts[2]),
        "utilization_gpu_pct": int(parts[3]),
    }


def get_system_info() -> dict[str, Any]:
    try:
        cpu_count = psutil.cpu_count(logical=True) or 0
    except Exception:
        cpu_count = 0
    try:
        vm = psutil.virtual_memory()
        memory_total_gb = _safe_float(vm.total / (1024**3))
        memory_used_gb = _safe_float(vm.used / (1024**3))
    except Exception:
        memory_total_gb = 0.0
        memory_used_gb = 0.0
    try:
        disk = psutil.disk_usage(".")
        disk_total_gb = _safe_float(disk.total / (1024**3))
        disk_used_gb = _safe_float(disk.used / (1024**3))
    except Exception:
        disk_total_gb = 0.0
        disk_used_gb = 0.0
    gpu = _get_gpu_info()
    return {
        "os": platform.platform(),
        "python": platform.python_version(),
        "cpu_count": cpu_count,
        "memory_total_gb": memory_total_gb,
        "memory_used_gb": memory_used_gb,
        "disk_total_gb": disk_total_gb,
        "disk_used_gb": disk_used_gb,
        "gpu": gpu,
        "has_gpu": gpu is not None,
    }


def format_startup_info(info: dict[str, Any]) -> str:
    gpu = info.get("gpu")
    gpu_str = "none"
    if isinstance(gpu, dict):
        gpu_str = f"{gpu.get('name')} {gpu.get('memory_total_mb')}MB"
    return (
        f"OS: {info.get('os')}\n"
        f"Python: {info.get('python')}\n"
        f"CPU cores: {info.get('cpu_count')}\n"
        f"RAM: {info.get('memory_used_gb')}/{info.get('memory_total_gb')} GB\n"
        f"Disk: {info.get('disk_used_gb')}/{info.get('disk_total_gb')} GB\n"
        f"GPU: {gpu_str}"
    )
