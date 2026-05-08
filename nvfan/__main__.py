"""Command-line interface for nv-fancurve."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from nvfan import __version__
from nvfan.config import load_config
from nvfan.daemon import FanDaemon, setup_logging
from nvfan.installer import DEFAULT_CONFIG_PATH, install, uninstall
from nvfan.nvidia import NvidiaError
from nvfan.presets import PRESETS


def cmd_run(args: argparse.Namespace) -> int:
    cfg = load_config(Path(args.config))
    setup_logging(cfg.log_file)
    daemon = FanDaemon(cfg)
    daemon.run()
    return 0


def cmd_install(args: argparse.Namespace) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    src = Path(args.config) if args.config else None
    install(config_source=src)
    return 0


def cmd_uninstall(args: argparse.Namespace) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    uninstall()
    return 0


def cmd_presets(args: argparse.Namespace) -> int:
    del args
    for name, info in PRESETS.items():
        print(f"\n{name}: {info['description']}")
        for temp, fan in info["curve"]:
            print(f"  {temp:>3} C -> {fan:>3}%")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    del args
    from nvfan.nvidia import list_gpus, query_stats

    for gpu_id in list_gpus():
        stats = query_stats(gpu_id)
        print(
            f"GPU {stats.index}: {stats.temp} C  fan={stats.fan_speed}%  "
            f"{stats.power_draw:.0f}W  {stats.clock_mhz}MHz"
        )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nv-fancurve",
        description="Temperature-based fan curve for NVIDIA GPUs on headless Linux.",
    )
    parser.add_argument("--version", action="version", version=f"nv-fancurve {__version__}")

    sub = parser.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run", help="Run the daemon in the foreground.")
    p_run.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="Path to config.toml")
    p_run.set_defaults(func=cmd_run)

    p_install = sub.add_parser("install", help="Install systemd services and start.")
    p_install.add_argument("--config", help="Custom config.toml to use as default", default=None)
    p_install.set_defaults(func=cmd_install)

    p_uninstall = sub.add_parser("uninstall", help="Stop and remove systemd services.")
    p_uninstall.set_defaults(func=cmd_uninstall)

    p_presets = sub.add_parser("presets", help="Show built-in fan curve presets.")
    p_presets.set_defaults(func=cmd_presets)

    p_status = sub.add_parser("status", help="Show current GPU temp/fan/power.")
    p_status.set_defaults(func=cmd_status)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except NvidiaError as e:
        print(f"nv-fancurve: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
