"""Configuration parsing and validation for nv-fancurve."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


@dataclass(frozen=True)
class CurvePoint:
    """A single (temperature, fan_speed) point on the curve."""

    temp: int
    fan: int

    def __post_init__(self) -> None:
        if not 0 <= self.temp <= 120:
            raise ValueError(f"Invalid temp {self.temp}: must be 0-120 C")
        if not 0 <= self.fan <= 100:
            raise ValueError(f"Invalid fan {self.fan}: must be 0-100%")


@dataclass
class Config:
    """Top-level nv-fancurve configuration."""

    interval_seconds: int = 5
    gpu_ids: list[int] = field(default_factory=lambda: [0])
    fan_id: int | str = 0
    fan_ids: list[int] | str | None = None
    fan_ids_by_gpu: dict[int, list[int]] | None = None
    display: str = ":1"
    log_file: str = "/var/log/nv-fancurve.log"
    log_only_on_change: bool = True
    curve: list[CurvePoint] = field(default_factory=list)
    hysteresis: int = 2

    def __post_init__(self) -> None:
        if not isinstance(self.interval_seconds, int) or self.interval_seconds <= 0:
            raise ValueError("interval_seconds must be a positive integer")
        if (
            not isinstance(self.gpu_ids, list)
            or not self.gpu_ids
            or any(not isinstance(gpu_id, int) or gpu_id < 0 for gpu_id in self.gpu_ids)
        ):
            raise ValueError("gpu_ids must be a non-empty list of non-negative integers")
        self.fan_ids = self._normalize_fan_ids(self.fan_ids, self.fan_id)
        if self.fan_ids == "all":
            self.fan_id = "all"
        else:
            self.fan_id = self.fan_ids[0]
        self.fan_ids_by_gpu = self._normalize_fan_ids_by_gpu(self.fan_ids_by_gpu)
        if not isinstance(self.display, str) or not self.display:
            raise ValueError("display must be a non-empty string")
        if not isinstance(self.log_file, str) or not self.log_file:
            raise ValueError("log_file must be a non-empty string")
        if not isinstance(self.log_only_on_change, bool):
            raise ValueError("log_only_on_change must be true or false")
        if not isinstance(self.hysteresis, int) or self.hysteresis < 0:
            raise ValueError("hysteresis must be a non-negative integer")

        temps = [point.temp for point in self.curve]
        if len(set(temps)) != len(temps):
            raise ValueError("Fan curve contains duplicate temperature points")

    @staticmethod
    def _normalize_fan_ids(fan_ids: list[int] | str | None, fan_id: int | str) -> list[int] | str:
        if fan_ids is None:
            if fan_id == "all":
                return "all"
            if not isinstance(fan_id, int) or fan_id < 0:
                raise ValueError("fan_id must be a non-negative integer or 'all'")
            return [fan_id]

        if fan_ids == "all":
            return "all"
        if (
            not isinstance(fan_ids, list)
            or not fan_ids
            or any(not isinstance(value, int) or value < 0 for value in fan_ids)
        ):
            raise ValueError("fan_ids must be a non-empty list of non-negative integers or 'all'")
        if len(set(fan_ids)) != len(fan_ids):
            raise ValueError("fan_ids contains duplicate fan IDs")
        return fan_ids

    @staticmethod
    def _normalize_fan_ids_by_gpu(
        fan_ids_by_gpu: dict[int, list[int]] | None,
    ) -> dict[int, list[int]] | None:
        if fan_ids_by_gpu is None:
            return None
        if not isinstance(fan_ids_by_gpu, dict):
            raise ValueError("fan_ids_by_gpu must be a table of GPU IDs to fan ID lists")

        normalized: dict[int, list[int]] = {}
        for raw_gpu_id, fan_ids in fan_ids_by_gpu.items():
            try:
                gpu_id = int(raw_gpu_id)
            except (TypeError, ValueError) as e:
                raise ValueError("fan_ids_by_gpu keys must be GPU IDs") from e
            if gpu_id < 0:
                raise ValueError("fan_ids_by_gpu keys must be non-negative GPU IDs")
            normalized_fan_ids = Config._normalize_fan_ids(fan_ids, 0)
            if normalized_fan_ids == "all":
                raise ValueError("fan_ids_by_gpu values must be fan ID lists")
            assert isinstance(normalized_fan_ids, list)
            normalized[gpu_id] = normalized_fan_ids
        return normalized

    def fan_ids_for_gpu(self, gpu_id: int) -> list[int] | str:
        """Return the fan IDs that should be controlled for one GPU."""
        if self.fan_ids_by_gpu and gpu_id in self.fan_ids_by_gpu:
            return self.fan_ids_by_gpu[gpu_id]
        if self.fan_ids is None:
            raise ValueError("No fan IDs configured")
        return self.fan_ids

    def fan_for_temp(self, temp: int) -> int:
        """Return fan speed (%) for a given temperature using a piecewise-linear curve."""
        if not self.curve:
            raise ValueError("Empty fan curve")

        sorted_curve = sorted(self.curve, key=lambda p: p.temp)

        if temp <= sorted_curve[0].temp:
            return sorted_curve[0].fan
        if temp >= sorted_curve[-1].temp:
            return sorted_curve[-1].fan

        for i in range(len(sorted_curve) - 1):
            lo, hi = sorted_curve[i], sorted_curve[i + 1]
            if lo.temp <= temp < hi.temp:
                ratio = (temp - lo.temp) / (hi.temp - lo.temp)
                fan = lo.fan + ratio * (hi.fan - lo.fan)
                return int(round(fan))

        return sorted_curve[-1].fan


def _known_config_keys() -> set[str]:
    return {field.name for field in fields(Config)}


def _load_curve(curve_data: Any, path: Path) -> list[CurvePoint]:
    if not isinstance(curve_data, list) or not curve_data:
        raise ValueError(f"Config {path} has no curve points")

    curve: list[CurvePoint] = []
    for i, point in enumerate(curve_data, start=1):
        if not isinstance(point, dict):
            raise ValueError(f"Curve point #{i} must be a TOML table")
        unknown = set(point) - {"temp", "fan"}
        if unknown:
            raise ValueError(f"Unknown curve key(s) in point #{i}: {', '.join(sorted(unknown))}")
        if "temp" not in point or "fan" not in point:
            raise ValueError(f"Curve point #{i} must include temp and fan")
        curve.append(CurvePoint(temp=point["temp"], fan=point["fan"]))
    return curve


def load_config(path: Path) -> Config:
    """Load and validate a TOML config file."""
    with path.open("rb") as f:
        data = tomllib.load(f)

    if not isinstance(data, dict):
        raise ValueError(f"Config {path} must be a TOML table")

    unknown = set(data) - _known_config_keys()
    if unknown:
        raise ValueError(f"Unknown config key(s): {', '.join(sorted(unknown))}")
    if "fan_id" in data and "fan_ids" in data:
        raise ValueError("Config cannot include both fan_id and fan_ids")

    curve = _load_curve(data.get("curve", []), path)
    options = {key: value for key, value in data.items() if key != "curve"}
    return Config(curve=curve, **options)
