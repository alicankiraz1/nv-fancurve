# Dual Fan GPU Support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Add first-class dual/multi-fan GPU support so one `nv-fancurve` daemon sets every configured fan for each GPU.

**Architecture:** Keep the Python package namespace as `nvfan`, but expose multi-fan behavior through config and NVIDIA wrapper APIs. `Config` will accept modern `fan_ids = [0, 1]` and legacy `fan_id = 0`; the daemon will loop over `config.fan_ids` in the existing single service. Installer code will detect fan IDs with `nvidia-settings -q fans` and update the generated default config before systemd starts the daemon.

**Tech Stack:** Python 3.9+, dataclasses, TOML parsing via `tomllib`/`tomli`, subprocess wrappers around `nvidia-smi` and `nvidia-settings`, pytest, ruff.

---

## File Map

- Modify `nvfan/config.py`: add `fan_ids`, preserve legacy `fan_id`, parse `fan_id = "all"` as an installer-only/user-facing shortcut when fan IDs can be detected, validate IDs, and expose the list the daemon uses.
- Modify `nvfan/nvidia.py`: add `list_fans(display=":1")`, add `set_fan_speeds(...)`, keep `set_fan_speed(...)` for compatibility.
- Modify `nvfan/daemon.py`: set all configured fans in `_handle_gpu` while keeping one daemon loop and one shutdown path.
- Modify `nvfan/installer.py`: after copying default config, query `nvidia-settings -q fans` and write detected `fan_ids` into `/etc/nv-fancurve/config.toml`; keep install working if detection fails.
- Modify `configs/*.toml` and `nvfan/assets/configs/*.toml`: replace `fan_id = 0` with `fan_ids = [0]`.
- Modify `README.md` and `CHANGELOG.md`: document `fan_ids`, `fan_id = "all"`, install-time detection, and dual-fan behavior.
- Add or modify tests under `tests/`: cover config compatibility, fan parsing, daemon multi-fan writes, installer config update, and CLI/documentation behavior.

## Task 1: Config Compatibility and Validation

**Files:**
- Modify: `tests/test_config.py`
- Modify: `nvfan/config.py`

- [x] **Step 1: Write failing tests**

Add tests showing modern list config, legacy int config, all-fan sentinel, and invalid values:

```python
def test_load_config_reads_fan_ids(tmp_path):
    path = write_config(tmp_path, """
interval_seconds = 5
fan_ids = [0, 1]

[[curve]]
temp = 50
fan = 40
""")

    cfg = load_config(path)

    assert cfg.fan_ids == [0, 1]
    assert cfg.fan_id == 0


def test_load_config_accepts_legacy_fan_id(tmp_path):
    path = write_config(tmp_path, """
fan_id = 2

[[curve]]
temp = 50
fan = 40
""")

    cfg = load_config(path)

    assert cfg.fan_ids == [2]
    assert cfg.fan_id == 2


def test_load_config_accepts_all_fan_sentinel(tmp_path):
    path = write_config(tmp_path, """
fan_id = "all"

[[curve]]
temp = 50
fan = 40
""")

    cfg = load_config(path)

    assert cfg.fan_ids == "all"


def test_config_rejects_invalid_fan_ids():
    with pytest.raises(ValueError, match="fan_ids"):
        Config(fan_ids=[], curve=[CurvePoint(50, 40)])
    with pytest.raises(ValueError, match="fan_ids"):
        Config(fan_ids=[0, -1], curve=[CurvePoint(50, 40)])
```

- [x] **Step 2: Verify red**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest tests/test_config.py -q -p no:cacheprovider
```

Expected: fails because `Config` has no `fan_ids` field and `fan_id = "all"` is invalid.

- [x] **Step 3: Implement minimal config support**

Update `Config` with `fan_ids: list[int] | str | None = None`, keep `fan_id: int | str = 0`, derive `fan_ids` in `__post_init__`, reject duplicate and negative fan IDs, and update `_known_config_keys()`.

- [x] **Step 4: Verify green**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest tests/test_config.py -q -p no:cacheprovider
```

Expected: all config tests pass.

## Task 2: NVIDIA Fan Discovery and Multi-Set Wrapper

**Files:**
- Create: `tests/test_nvidia.py`
- Modify: `nvfan/nvidia.py`

- [x] **Step 1: Write failing tests**

Add tests for parsing `nvidia-settings -q fans` output and sending both fan assignments in one command:

```python
from nvfan import nvidia


def test_list_fans_parses_nvidia_settings_output(monkeypatch):
    def fake_run(cmd, env=None, timeout=10):
        assert cmd == ["nvidia-settings", "-q", "fans"]
        assert env["DISPLAY"] == ":1"
        return "  Attribute 'fans' (host:1): 2.\\n    [fan:0]\\n    [fan:1]\\n"

    monkeypatch.setattr(nvidia, "_run", fake_run)

    assert nvidia.list_fans(":1") == [0, 1]


def test_set_fan_speeds_sets_every_fan(monkeypatch):
    calls = []

    def fake_run(cmd, env=None, timeout=10):
        calls.append((cmd, env))
        return ""

    monkeypatch.setattr(nvidia, "_run", fake_run)

    nvidia.set_fan_speeds(0, [0, 1], 65, ":1")

    assert calls[0][0] == [
        "nvidia-settings",
        "-a", "[gpu:0]/GPUFanControlState=1",
        "-a", "[fan:0]/GPUTargetFanSpeed=65",
        "-a", "[fan:1]/GPUTargetFanSpeed=65",
    ]
    assert calls[0][1]["DISPLAY"] == ":1"
```

- [x] **Step 2: Verify red**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest tests/test_nvidia.py -q -p no:cacheprovider
```

Expected: fails because `list_fans` and `set_fan_speeds` do not exist.

- [x] **Step 3: Implement wrapper support**

Add `list_fans(display=":1") -> list[int]`, parse every `[fan:N]` occurrence with a regex, and add `set_fan_speeds(gpu_id, fan_ids, speed_pct, display)` that enables manual mode once and appends one target assignment per fan.

- [x] **Step 4: Verify green**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest tests/test_nvidia.py -q -p no:cacheprovider
```

Expected: tests pass.

## Task 3: Daemon Applies One Curve to All Configured Fans

**Files:**
- Create: `tests/test_daemon.py`
- Modify: `nvfan/daemon.py`

- [x] **Step 1: Write failing test**

Test `_handle_gpu` with two configured fan IDs:

```python
from nvfan.config import Config, CurvePoint
from nvfan.daemon import FanDaemon
from nvfan.nvidia import GpuStats


def test_handle_gpu_sets_all_configured_fans(monkeypatch):
    calls = []
    cfg = Config(curve=[CurvePoint(50, 40), CurvePoint(80, 100)], fan_ids=[0, 1])
    daemon = FanDaemon(cfg)

    monkeypatch.setattr(
        "nvfan.daemon.query_stats",
        lambda gpu_id: GpuStats(gpu_id, temp=65, fan_speed=0, power_draw=250.0, clock_mhz=1800),
    )
    monkeypatch.setattr(
        "nvfan.daemon.set_fan_speeds",
        lambda gpu_id, fan_ids, speed_pct, display: calls.append(
            (gpu_id, fan_ids, speed_pct, display)
        ),
    )

    daemon._handle_gpu(0)

    assert calls == [(0, [0, 1], 70, ":1")]
```

- [x] **Step 2: Verify red**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest tests/test_daemon.py -q -p no:cacheprovider
```

Expected: fails because daemon imports/calls `set_fan_speed` with one fan.

- [x] **Step 3: Implement daemon support**

Import `set_fan_speeds` and call `set_fan_speeds(gpu_id, self.config.fan_ids, target_fan, self.config.display)`. Keep shutdown unchanged because `GPUFanControlState=0` is per GPU.

- [x] **Step 4: Verify green**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest tests/test_daemon.py -q -p no:cacheprovider
```

Expected: daemon test passes.

## Task 4: Install-Time Fan Detection

**Files:**
- Create: `tests/test_installer.py`
- Modify: `nvfan/installer.py`

- [x] **Step 1: Write failing tests**

Add tests for writing detected fan IDs and tolerating detection failure:

```python
from pathlib import Path

from nvfan.installer import _apply_detected_fan_ids


def test_apply_detected_fan_ids_replaces_legacy_fan_id(tmp_path, monkeypatch):
    config = tmp_path / "config.toml"
    config.write_text("fan_id = 0\\n\\n[[curve]]\\ntemp = 50\\nfan = 40\\n")
    monkeypatch.setattr("nvfan.installer.list_fans", lambda display: [0, 1])

    _apply_detected_fan_ids(config, ":1")

    text = config.read_text()
    assert "fan_ids = [0, 1]" in text
    assert "fan_id = 0" not in text


def test_apply_detected_fan_ids_keeps_config_when_detection_fails(tmp_path, monkeypatch):
    config = tmp_path / "config.toml"
    original = "fan_ids = [0]\\n\\n[[curve]]\\ntemp = 50\\nfan = 40\\n"
    config.write_text(original)

    def fail(display):
        raise RuntimeError("x unavailable")

    monkeypatch.setattr("nvfan.installer.list_fans", fail)

    _apply_detected_fan_ids(config, ":1")

    assert config.read_text() == original
```

- [x] **Step 2: Verify red**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest tests/test_installer.py -q -p no:cacheprovider
```

Expected: fails because `_apply_detected_fan_ids` does not exist.

- [x] **Step 3: Implement installer helper**

Add `_apply_detected_fan_ids(config_path, display)` that calls `list_fans(display)`, replaces an existing `fan_id = ...` or `fan_ids = ...` top-level line with `fan_ids = [0, 1]`, logs and returns if no fans or detection failure, and call it after `_copy_default_config(...)` in `install()`.

- [x] **Step 4: Verify green**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest tests/test_installer.py -q -p no:cacheprovider
```

Expected: installer tests pass.

## Task 5: Configs and Documentation

**Files:**
- Modify: `configs/*.toml`
- Modify: `nvfan/assets/configs/*.toml`
- Modify: `README.md`
- Modify: `CHANGELOG.md`

- [x] **Step 1: Update preset configs**

Replace `fan_id = 0` with `fan_ids = [0]` in all checked-in TOML presets and packaged asset copies.

- [x] **Step 2: Update README**

Document:

```toml
fan_ids = [0, 1]
```

and mention:

```toml
fan_id = "all"
```

as a shortcut for install-time fan discovery. State that legacy `fan_id = 0` remains accepted.

- [x] **Step 3: Update changelog**

Add an unreleased section:

```markdown
## [Unreleased]

### Added

- Dual/multi-fan GPU support with `fan_ids = [0, 1]`.
- Install-time fan detection using `nvidia-settings -q fans`.
```

- [x] **Step 4: Verify config docs**

Run:

```bash
rg -n "fan_id|fan_ids|dual|multi-fan" README.md CHANGELOG.md configs nvfan/assets/configs
```

Expected: docs describe `fan_ids`, legacy references are intentional, and presets use `fan_ids`.

## Task 6: Full Verification and Publish

**Files:**
- Verify all modified files

- [x] **Step 1: Run all tests**

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider
```

Expected: all tests pass.

- [x] **Step 2: Run lint**

```bash
.venv/bin/ruff check . --no-cache
```

Expected: all checks pass.

- [x] **Step 3: Build package**

```bash
rm -rf /tmp/nv-fancurve-dist-dual-fan
mkdir -p /tmp/nv-fancurve-dist-dual-fan
.venv/bin/python -m build --sdist --wheel --outdir /tmp/nv-fancurve-dist-dual-fan
```

Expected: sdist and wheel build with no warnings.

- [x] **Step 4: Clean generated artifacts**

```bash
rm -rf build nv_fancurve.egg-info .pytest_cache .ruff_cache .mypy_cache
```

Expected: `git status --short --branch` shows only intentional source/doc/test changes.

- [x] **Step 5: Commit and push**

```bash
git add docs/superpowers/plans/2026-05-09-dual-fan-gpu-support.md \
  tests/test_config.py tests/test_nvidia.py tests/test_daemon.py tests/test_installer.py \
  nvfan/config.py nvfan/nvidia.py nvfan/daemon.py nvfan/installer.py \
  configs/*.toml nvfan/assets/configs/*.toml README.md CHANGELOG.md
git commit -m "feat: add dual fan GPU support"
git push
```

Expected: branch pushes cleanly to `origin/main`.
