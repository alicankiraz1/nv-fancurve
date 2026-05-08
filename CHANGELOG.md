# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-05-08

### Added

- Initial `nv-fancurve` command-line package.
- Piecewise-linear TOML fan curve parser with validation.
- Foreground daemon loop with hysteresis and change-only logging.
- `nvidia-smi` stats wrapper and `nvidia-settings` fan control wrapper.
- Headless Xorg config generation with `Coolbits=28`.
- `nv-fancurve install` and `nv-fancurve uninstall` systemd workflow.
- Built-in `aggressive`, `balanced`, and `silent` fan curve presets.
- Unit tests for curve interpolation and TOML config loading.
- GitHub Actions test workflow for Python 3.9 through 3.12.
