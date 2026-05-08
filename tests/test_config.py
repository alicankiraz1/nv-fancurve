from pathlib import Path

import pytest

from nvfan.config import Config, CurvePoint, load_config


def write_config(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "config.toml"
    path.write_text(content)
    return path


def test_load_config_reads_top_level_options_and_curve(tmp_path):
    path = write_config(
        tmp_path,
        """
interval_seconds = 7
gpu_ids = [0, 1]
fan_id = 2
display = ":2"
log_file = "/tmp/nv-fancurve.log"
log_only_on_change = false
hysteresis = 4

[[curve]]
temp = 45
fan = 30

[[curve]]
temp = 80
fan = 90
""",
    )

    cfg = load_config(path)

    assert cfg.interval_seconds == 7
    assert cfg.gpu_ids == [0, 1]
    assert cfg.fan_id == 2
    assert cfg.display == ":2"
    assert cfg.log_file == "/tmp/nv-fancurve.log"
    assert cfg.log_only_on_change is False
    assert cfg.hysteresis == 4
    assert cfg.curve == [CurvePoint(45, 30), CurvePoint(80, 90)]


def test_load_config_rejects_missing_curve(tmp_path):
    path = write_config(tmp_path, "interval_seconds = 5\n")

    with pytest.raises(ValueError, match="no curve points"):
        load_config(path)


def test_load_config_rejects_unknown_keys(tmp_path):
    path = write_config(
        tmp_path,
        """
interval_seconds = 5
unknown = "nope"

[[curve]]
temp = 50
fan = 40
""",
    )

    with pytest.raises(ValueError, match="Unknown config key"):
        load_config(path)


def test_config_rejects_invalid_runtime_options():
    with pytest.raises(ValueError, match="interval_seconds"):
        Config(interval_seconds=0, curve=[CurvePoint(50, 40)])
    with pytest.raises(ValueError, match="gpu_ids"):
        Config(gpu_ids=[], curve=[CurvePoint(50, 40)])
    with pytest.raises(ValueError, match="hysteresis"):
        Config(hysteresis=-1, curve=[CurvePoint(50, 40)])
