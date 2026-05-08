"""Wrappers around nvidia-smi and nvidia-settings."""

from __future__ import annotations

import logging
import os
import re
import subprocess
from dataclasses import dataclass

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class GpuStats:
    index: int
    temp: int
    fan_speed: int
    power_draw: float
    clock_mhz: int


class NvidiaError(Exception):
    """Raised when nvidia-smi or nvidia-settings fails."""


def _run(cmd: list[str], env: dict[str, str] | None = None, timeout: int = 10) -> str:
    """Run a command, return stdout, raise on error."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            check=False,
        )
    except subprocess.TimeoutExpired as e:
        raise NvidiaError(f"Command timed out: {' '.join(cmd)}") from e
    except FileNotFoundError as e:
        raise NvidiaError(f"Command not found: {cmd[0]}") from e

    if result.returncode != 0:
        stderr = result.stderr.strip()
        raise NvidiaError(f"Command failed (rc={result.returncode}): {' '.join(cmd)}\n{stderr}")
    return result.stdout


def _is_missing(value: str) -> bool:
    return value.strip() in {"", "N/A", "[N/A]"}


def _parse_int(value: str, default: int = 0) -> int:
    return default if _is_missing(value) else int(value)


def _parse_float(value: str, default: float = 0.0) -> float:
    return default if _is_missing(value) else float(value)


def query_stats(gpu_id: int = 0) -> GpuStats:
    """Read current stats for one GPU using nvidia-smi."""
    out = _run(
        [
            "nvidia-smi",
            f"--id={gpu_id}",
            "--query-gpu=index,temperature.gpu,fan.speed,power.draw,clocks.current.graphics",
            "--format=csv,noheader,nounits",
        ]
    )
    first_line = out.strip().splitlines()[0] if out.strip() else ""
    parts = [p.strip() for p in first_line.split(",")]
    if len(parts) < 5:
        raise NvidiaError(f"Unexpected nvidia-smi output: {out!r}")

    return GpuStats(
        index=int(parts[0]),
        temp=int(parts[1]),
        fan_speed=_parse_int(parts[2]),
        power_draw=_parse_float(parts[3]),
        clock_mhz=_parse_int(parts[4]),
    )


def set_fan_speed(gpu_id: int, fan_id: int, speed_pct: int, display: str = ":1") -> None:
    """Set fan speed for a single fan via nvidia-settings on the given X display."""
    set_fan_speeds(gpu_id, [fan_id], speed_pct, display)


def list_fans(display: str = ":1") -> list[int]:
    """Return fan IDs reported by nvidia-settings on the given X display."""
    env = os.environ.copy()
    env["DISPLAY"] = display

    out = _run(["nvidia-settings", "-q", "fans"], env=env)
    return sorted({int(match) for match in re.findall(r"\[fan:(\d+)\]", out)})


def set_fan_speeds(
    gpu_id: int,
    fan_ids: list[int] | str,
    speed_pct: int,
    display: str = ":1",
) -> None:
    """Set fan speed for every configured fan via nvidia-settings."""
    if not 0 <= speed_pct <= 100:
        raise ValueError(f"Invalid speed {speed_pct}: must be 0-100")

    env = os.environ.copy()
    env["DISPLAY"] = display

    resolved_fan_ids = list_fans(display) if fan_ids == "all" else fan_ids
    if not resolved_fan_ids:
        raise NvidiaError("No NVIDIA fans found")

    cmd = ["nvidia-settings", "-a", f"[gpu:{gpu_id}]/GPUFanControlState=1"]
    for fan_id in resolved_fan_ids:
        cmd.extend(["-a", f"[fan:{fan_id}]/GPUTargetFanSpeed={speed_pct}"])

    _run(cmd, env=env)


def set_fan_auto(gpu_id: int, display: str = ":1") -> None:
    """Restore automatic fan control."""
    env = os.environ.copy()
    env["DISPLAY"] = display

    _run(
        [
            "nvidia-settings",
            "-a",
            f"[gpu:{gpu_id}]/GPUFanControlState=0",
        ],
        env=env,
    )


def list_gpus() -> list[int]:
    """Return available NVIDIA GPU indices."""
    out = _run(["nvidia-smi", "--query-gpu=index", "--format=csv,noheader,nounits"])
    return [int(line.strip()) for line in out.splitlines() if line.strip()]
