"""Main fan curve daemon loop."""

from __future__ import annotations

import logging
import signal
import sys
import time
from pathlib import Path
from types import FrameType

from nvfan.config import Config
from nvfan.nvidia import NvidiaError, query_stats, set_fan_auto, set_fan_speed
from nvfan.xorg import is_xorg_running

log = logging.getLogger(__name__)


class FanDaemon:
    """Long-running daemon that applies configured fan speeds to each GPU."""

    def __init__(self, config: Config):
        self.config = config
        self.last_temps: dict[int, int] = {}
        self.last_fans: dict[int, int] = {}
        self._running = True

    def _check_xorg(self) -> None:
        if not is_xorg_running(self.config.display):
            raise RuntimeError(
                f"Xorg not running on {self.config.display}. "
                "Start nv-fancurve-xorg.service first."
            )

    def _handle_gpu(self, gpu_id: int) -> None:
        try:
            stats = query_stats(gpu_id)
        except NvidiaError as e:
            log.error("[gpu %d] query failed: %s", gpu_id, e)
            return

        last_temp = self.last_temps.get(gpu_id)
        if last_temp is not None and abs(stats.temp - last_temp) < self.config.hysteresis:
            return

        target_fan = self.config.fan_for_temp(stats.temp)
        last_fan = self.last_fans.get(gpu_id)

        if last_fan == target_fan and last_temp is not None:
            self.last_temps[gpu_id] = stats.temp
            return

        try:
            set_fan_speed(gpu_id, self.config.fan_id, target_fan, self.config.display)
        except NvidiaError as e:
            log.error("[gpu %d] set fan failed: %s", gpu_id, e)
            return

        self.last_temps[gpu_id] = stats.temp
        self.last_fans[gpu_id] = target_fan

        if not self.config.log_only_on_change or last_fan != target_fan:
            log.info(
                "[gpu %d] temp=%d C fan=%d%% power=%.0fW clock=%dMHz",
                gpu_id,
                stats.temp,
                target_fan,
                stats.power_draw,
                stats.clock_mhz,
            )

    def run(self) -> None:
        signal.signal(signal.SIGTERM, self._stop)
        signal.signal(signal.SIGINT, self._stop)

        self._check_xorg()
        log.info(
            "nv-fancurve starting: gpus=%s interval=%ds",
            self.config.gpu_ids,
            self.config.interval_seconds,
        )

        while self._running:
            for gpu_id in self.config.gpu_ids:
                self._handle_gpu(gpu_id)
            time.sleep(self.config.interval_seconds)

        log.info("Shutting down, restoring auto fan control")
        for gpu_id in self.config.gpu_ids:
            try:
                set_fan_auto(gpu_id, self.config.display)
            except NvidiaError as e:
                log.warning("[gpu %d] could not restore auto: %s", gpu_id, e)

    def _stop(self, signum: int, frame: FrameType | None) -> None:
        del frame
        log.info("Received signal %d, stopping", signum)
        self._running = False


def setup_logging(log_file: str) -> None:
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    fmt = "%(asctime)s | %(levelname)s | %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    file_handler = logging.FileHandler(log_path)
    file_handler.setFormatter(logging.Formatter(fmt, datefmt))

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(logging.Formatter(fmt, datefmt))

    logging.basicConfig(level=logging.INFO, handlers=[file_handler, stream_handler], force=True)
