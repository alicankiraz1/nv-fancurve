# nv-fancurve

[![PyPI](https://img.shields.io/badge/PyPI-coming%20soon-blue)](https://pypi.org/project/nv-fancurve/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)](pyproject.toml)
[![Test](https://github.com/alicankiraz1/nv-fancurve/actions/workflows/test.yml/badge.svg)](https://github.com/alicankiraz1/nv-fancurve/actions/workflows/test.yml)

`nv-fancurve` is a small systemd-managed fan curve daemon for NVIDIA GPUs on headless Linux.
It exists for sustained LLM inference, fine-tuning, dataset generation, and other long-running
GPU workloads where default workstation fan behavior can let RTX 50 / Blackwell-class cards sit
hot for hours. In some rigs that thermal stress shows up as throttling, instability, or
GSP-timeout-style failures; `nv-fancurve` keeps the curve explicit, inspectable, and easy to tune.

```text
Default curve

Fan %
100 |                                      *
 90 |                                 *
 80 |                            *
 70 |                       *
 60 |
 50 |                 *
 40 |          *
 30 |    *
    +----+----+----+----+----+----+----+---- Temp C
        45   55   60   70   75   80   85
```

## Who This Is For

- Homelabbers running NVIDIA cards in headless Linux machines.
- ML researchers and engineers doing sustained inference, SFT, or training runs.
- Datacenter operators who want a simple TOML fan curve instead of a manual GUI workflow.
- Anyone using cards such as RTX PRO 6000, RTX 5090, A100, or similar NVIDIA GPUs in rigs where
  the stock fan curve is too conservative for 24/7 work.

## Requirements

- Linux with systemd, tested target: Ubuntu 22.04 / 24.04 / 26.04 class systems.
- NVIDIA driver 470 or newer.
- `nvidia-smi`.
- `nvidia-settings`.
- Xorg. `nv-fancurve install` creates a tiny headless Xorg display on `:1`.
- Python 3.9 or newer.
- `pipx` for Ubuntu 24.04+ / Debian systems that block global `pip install` via PEP 668.
- Root access for installation, because systemd units and `/etc/X11` config are written.

## Quickstart

Ubuntu 24.04+ marks the system Python environment as externally managed, so install the CLI with
`pipx` instead of global `pip`.

```bash
sudo apt update
sudo apt install pipx python3-venv xserver-xorg-core xserver-xorg-video-dummy x11-xserver-utils nvidia-settings

pipx ensurepath
export PATH="$PATH:$HOME/.local/bin"
pipx install git+https://github.com/alicankiraz1/nv-fancurve.git

sudo "$(command -v nv-fancurve)" install

systemctl status nv-fancurve --no-pager
```

If you already cloned this repository, install from the local checkout:

```bash
sudo apt update
sudo apt install pipx python3-venv xserver-xorg-core xserver-xorg-video-dummy x11-xserver-utils nvidia-settings

cd nv-fancurve
export PATH="$PATH:$HOME/.local/bin"
pipx install --force .
sudo "$(command -v nv-fancurve)" install
systemctl status nv-fancurve --no-pager
```

The `export PATH=...` line makes the `pipx` command shim visible in the current shell. The quoted
`sudo "$(command -v nv-fancurve)" install` form matters because `sudo` often uses a restricted PATH
and may not see `~/.local/bin/nv-fancurve`.

For local development from this repository, use a virtual environment:

```bash
sudo apt install python3-venv
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
python -m pytest -v
ruff check .
```

## How It Works

1. A tiny Xorg server starts at boot on `:1` with `Coolbits=28`.
2. The `nv-fancurve` daemon reads GPU temperature every `interval_seconds`.
3. It computes a target fan speed from a piecewise-linear curve.
4. It calls `nvidia-settings` with `DISPLAY=:1` to set every configured fan.
5. It logs only on fan changes by default and systemd restarts it on failure.
6. On shutdown, it restores automatic fan control.

## Configuration

The installed config lives at `/etc/nv-fancurve/config.toml`.

```toml
interval_seconds = 5
gpu_ids = [0]
fan_ids = [0]
display = ":1"
log_file = "/var/log/nv-fancurve.log"
log_only_on_change = true
hysteresis = 2

[[curve]]
temp = 45
fan = 30

[[curve]]
temp = 55
fan = 40

[[curve]]
temp = 60
fan = 50

[[curve]]
temp = 70
fan = 65

[[curve]]
temp = 75
fan = 75

[[curve]]
temp = 80
fan = 85

[[curve]]
temp = 85
fan = 100
```

Config fields:

- `interval_seconds`: how often the daemon samples GPU temperature.
- `gpu_ids`: NVIDIA GPU indices from `nvidia-smi`; use `[0, 1]` for two GPUs.
- `fan_ids`: fan indices passed to `nvidia-settings`; use `[0, 1]` for dual-fan cards.
- `fan_id`: legacy single-fan config key. `fan_id = 0` still works, and `fan_id = "all"` tells
  install-time detection to replace it with every fan reported by `nvidia-settings -q fans`.
- `display`: X display used by the headless Xorg service.
- `hysteresis`: minimum temperature movement before the daemon recalculates and writes a fan
  target. This avoids noisy fan changes around curve boundaries.
- `log_only_on_change`: when true, log only when the target fan speed changes.

Switch to a preset after installation:

```bash
sudo cp /usr/local/share/nv-fancurve/configs/silent.toml /etc/nv-fancurve/config.toml
sudo systemctl restart nv-fancurve
```

If your Python environment installs data files under a different prefix, use the repository copy
instead:

```bash
sudo cp configs/silent.toml /etc/nv-fancurve/config.toml
sudo systemctl restart nv-fancurve
```

## Built-In Presets

```text
$ nv-fancurve presets

aggressive: For 24/7 inference or training. Keeps GPU below about 75 C.
   45 C ->  30%
   55 C ->  40%
   60 C ->  50%
   70 C ->  65%
   75 C ->  75%
   80 C ->  85%
   85 C -> 100%

balanced: Reasonable default. Quiet at idle, ramps up under load.
   50 C ->  30%
   60 C ->  40%
   70 C ->  55%
   75 C ->  70%
   82 C ->  90%
   88 C -> 100%

silent: Prioritizes quiet operation. May allow 80 C+.
   50 C ->  25%
   65 C ->  35%
   75 C ->  50%
   82 C ->  75%
   88 C -> 100%
```

## CLI Reference

```bash
nv-fancurve run --config /etc/nv-fancurve/config.toml
nv-fancurve install
nv-fancurve uninstall
nv-fancurve status
nv-fancurve presets
```

`nv-fancurve run` stays in the foreground. The normal production path is
`sudo "$(command -v nv-fancurve)" install`, which installs and starts `nv-fancurve-xorg.service`
and `nv-fancurve.service`.

## Multi-GPU

Set multiple IDs in TOML:

```toml
gpu_ids = [0, 1]
```

The same curve is applied to each GPU. For unusual fan mappings, confirm fan indices with
`nvidia-settings -q fans` on the headless display.

## Multi-Fan GPUs

Set every fan you want the daemon to control:

```toml
fan_ids = [0, 1]
```

`nv-fancurve install` starts the headless Xorg service, runs `nvidia-settings -q fans`, and updates
the default config with every detected fan on first install. This avoids the common dual-fan failure
mode where one fan follows the curve while the other stays at the stock target.

For explicit auto-detection in a custom config, use:

```toml
fan_id = "all"
```

The daemon still runs as one systemd service and restores automatic GPU fan control once on shutdown.

## Troubleshooting

`nvidia-settings: Unable to find display :1`

Check the Xorg service:

```bash
systemctl status nv-fancurve-xorg
journalctl -u nv-fancurve-xorg -n 50 --no-pager
```

`Failed to set fan speed`

Confirm the generated Xorg config contains `Coolbits=28`:

```bash
sudo grep Coolbits /etc/X11/xorg.conf.d/10-nv-fancurve.conf
```

Fan control resets after reboot

Make sure both services are enabled:

```bash
sudo systemctl enable nv-fancurve-xorg nv-fancurve
```

Card ignores fan setting under load

Some cards enforce firmware limits. Combine fan control with a power limit:

```bash
sudo nvidia-smi -pl <watts>
```

## Alternatives

| Tool | Headless | Multi-curve | systemd | Config |
| --- | --- | --- | --- | --- |
| nv-fancurve | yes | yes, piecewise | yes | TOML |
| nvidia-settings GUI | no | no | no | manual |
| coolgpus | yes | step-based | manual | CLI args |
| nvidia-fan-control | yes | no | manual | hardcoded |

## Origin

`nv-fancurve` was extracted from a real cybersecurity LLM inference rig with an RTX PRO 6000 and dual
RTX 5090 cards. Stock fan behavior caused unnecessary thermal stress during 24/7 SFT dataset
generation, so the manual Xorg plus fan-curve setup became a small reusable daemon.

## Contributing

Pull requests are welcome. Please run:

```bash
make test
make lint
```

For more detail, see [CONTRIBUTING.md](CONTRIBUTING.md).

## Author

**Alican Kiraz**

[![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=flat&logo=linkedin&logoColor=white)](https://linkedin.com/in/alican-kiraz)
[![X](https://img.shields.io/badge/X-000000?style=flat&logo=x&logoColor=white)](https://x.com/AlicanKiraz0)
[![Medium](https://img.shields.io/badge/Medium-12100E?style=flat&logo=medium&logoColor=white)](https://alican-kiraz1.medium.com)
[![HuggingFace](https://img.shields.io/badge/HuggingFace-FFD21E?style=flat&logo=huggingface&logoColor=black)](https://huggingface.co/AlicanKiraz0)
[![GitHub](https://img.shields.io/badge/GitHub-181717?style=flat&logo=github&logoColor=white)](https://github.com/alicankiraz1)

## License

MIT. See [LICENSE](LICENSE).
