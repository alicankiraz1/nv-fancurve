"""Install and uninstall systemd units and Xorg config for nv-fancurve."""

from __future__ import annotations

import importlib.resources as resources
import logging
import os
import shutil
import subprocess
import sys
import time
from contextlib import suppress
from pathlib import Path

from nvfan.xorg import write_xorg_conf

log = logging.getLogger(__name__)

SYSTEMD_DIR = Path("/etc/systemd/system")
CONFIG_DIR = Path("/etc/nv-fancurve")
DEFAULT_CONFIG_PATH = CONFIG_DIR / "config.toml"

XORG_SERVICE = """\
[Unit]
Description=nv-fancurve headless Xorg for NVIDIA fan control
After=multi-user.target

[Service]
Type=simple
ExecStart=/usr/bin/Xorg :1 -config /etc/X11/xorg.conf.d/10-nv-fancurve.conf -nolisten tcp
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
"""

DAEMON_SERVICE = """\
[Unit]
Description=nv-fancurve GPU fan curve daemon
After=nv-fancurve-xorg.service nvidia-persistenced.service
Requires=nv-fancurve-xorg.service

[Service]
Type=simple
ExecStartPre=/bin/sleep 5
ExecStart={command} run --config {config_path}
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""


def _systemctl(*args: str) -> None:
    subprocess.run(["systemctl", *args], check=True)


def _require_root() -> None:
    if hasattr(os, "geteuid") and os.geteuid() != 0:
        log.error("This action requires root. Try: sudo nv-fancurve ...")
        sys.exit(1)


def _copy_default_config(destination: Path, config_source: Path | None = None) -> None:
    if config_source is not None:
        shutil.copy(config_source, destination)
        return

    source_tree_config = Path(__file__).resolve().parent.parent / "configs" / "default.toml"
    if source_tree_config.exists():
        shutil.copy(source_tree_config, destination)
        return

    packaged = resources.files("nvfan.assets.configs").joinpath("default.toml")
    with resources.as_file(packaged) as packaged_path:
        shutil.copy(packaged_path, destination)


def _command() -> str:
    command_path = shutil.which("nv-fancurve")
    if command_path:
        return command_path
    return f"{sys.executable} -m nvfan"


def install(config_source: Path | None = None) -> None:
    """Install Xorg config, systemd units, and a default config."""
    _require_root()

    write_xorg_conf()

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not DEFAULT_CONFIG_PATH.exists():
        _copy_default_config(DEFAULT_CONFIG_PATH, config_source)
        log.info("Installed default config to %s", DEFAULT_CONFIG_PATH)
    else:
        log.info("Config already exists at %s; not overwriting", DEFAULT_CONFIG_PATH)

    (SYSTEMD_DIR / "nv-fancurve-xorg.service").write_text(XORG_SERVICE)
    (SYSTEMD_DIR / "nv-fancurve.service").write_text(
        DAEMON_SERVICE.format(command=_command(), config_path=DEFAULT_CONFIG_PATH)
    )

    _systemctl("daemon-reload")
    _systemctl("enable", "--now", "nv-fancurve-xorg.service")
    time.sleep(3)
    _systemctl("enable", "--now", "nv-fancurve.service")

    log.info("nv-fancurve installed and running. Check: systemctl status nv-fancurve")


def uninstall() -> None:
    """Stop, disable, and remove all nv-fancurve units and Xorg config."""
    _require_root()

    for unit in ("nv-fancurve.service", "nv-fancurve-xorg.service"):
        with suppress(subprocess.CalledProcessError):
            _systemctl("disable", "--now", unit)
        unit_path = SYSTEMD_DIR / unit
        if unit_path.exists():
            unit_path.unlink()

    _systemctl("daemon-reload")

    xorg_conf = Path("/etc/X11/xorg.conf.d/10-nv-fancurve.conf")
    if xorg_conf.exists():
        xorg_conf.unlink()

    log.info("nv-fancurve uninstalled. Configs in /etc/nv-fancurve were kept.")
