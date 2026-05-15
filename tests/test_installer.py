from pathlib import Path

from nvfan.installer import XORG_SERVICE, _apply_detected_fan_ids, _apply_detected_hardware_config
from nvfan.nvidia import NvidiaError


def test_xorg_service_does_not_order_after_own_install_target():
    assert "WantedBy=multi-user.target" in XORG_SERVICE
    assert "After=multi-user.target" not in XORG_SERVICE

    packaged_unit = Path(__file__).resolve().parent.parent / "systemd" / "nv-fancurve-xorg.service"
    text = packaged_unit.read_text()
    assert "WantedBy=multi-user.target" in text
    assert "After=multi-user.target" not in text


def test_apply_detected_fan_ids_replaces_legacy_fan_id(tmp_path, monkeypatch):
    config = tmp_path / "config.toml"
    config.write_text("fan_id = 0\n\n[[curve]]\ntemp = 50\nfan = 40\n")
    monkeypatch.setattr("nvfan.installer.list_fans", lambda display: [0, 1])

    _apply_detected_fan_ids(config, ":1")

    text = config.read_text()
    assert "fan_ids = [0, 1]" in text
    assert "fan_id = 0" not in text


def test_apply_detected_fan_ids_replaces_existing_fan_ids(tmp_path, monkeypatch):
    config = tmp_path / "config.toml"
    config.write_text("fan_ids = [0]\n\n[[curve]]\ntemp = 50\nfan = 40\n")
    monkeypatch.setattr("nvfan.installer.list_fans", lambda display: [0, 1])

    _apply_detected_fan_ids(config, ":1")

    assert "fan_ids = [0, 1]" in config.read_text()


def test_apply_detected_fan_ids_collapses_ambiguous_fan_keys(tmp_path, monkeypatch):
    config = tmp_path / "config.toml"
    config.write_text("fan_id = 0\nfan_ids = [0]\n\n[[curve]]\ntemp = 50\nfan = 40\n")
    monkeypatch.setattr("nvfan.installer.list_fans", lambda display: [0, 1])

    _apply_detected_fan_ids(config, ":1")

    text = config.read_text()
    assert text.count("fan_ids = [0, 1]") == 1
    assert "fan_id = 0" not in text
    assert "fan_ids = [0]\n" not in text


def test_apply_detected_fan_ids_keeps_config_when_detection_fails(tmp_path, monkeypatch):
    config = tmp_path / "config.toml"
    original = "fan_ids = [0]\n\n[[curve]]\ntemp = 50\nfan = 40\n"
    config.write_text(original)

    def fail(display):
        raise RuntimeError("x unavailable")

    monkeypatch.setattr("nvfan.installer.list_fans", fail)

    _apply_detected_fan_ids(config, ":1")

    assert config.read_text() == original


def test_apply_detected_hardware_config_writes_gpu_fan_map(tmp_path, monkeypatch):
    config = tmp_path / "config.toml"
    config.write_text(
        "gpu_ids = [0]\nfan_ids = [0, 1, 2, 3, 4, 5]\n\n[[curve]]\ntemp = 50\nfan = 40\n"
    )
    monkeypatch.setattr("nvfan.installer.list_gpus", lambda: [0, 1])
    monkeypatch.setattr(
        "nvfan.installer.list_fan_map",
        lambda gpu_ids, display: {0: [0, 1, 2], 1: [3, 4, 5]},
    )

    _apply_detected_hardware_config(config, ":1")

    text = config.read_text()
    assert "gpu_ids = [0, 1]" in text
    assert "fan_ids = [0, 1, 2, 3, 4, 5]" not in text
    assert "[fan_ids_by_gpu]" in text
    assert "0 = [0, 1, 2]" in text
    assert "1 = [3, 4, 5]" in text


def test_apply_detected_hardware_config_splits_global_fans_when_per_gpu_query_fails(
    tmp_path, monkeypatch
):
    config = tmp_path / "config.toml"
    config.write_text(
        "gpu_ids = [0]\nfan_ids = [0, 1, 2, 3, 4, 5]\n\n[[curve]]\ntemp = 50\nfan = 40\n"
    )
    monkeypatch.setattr("nvfan.installer.list_gpus", lambda: [0, 1])

    def fail_fan_map(gpu_ids, display):
        raise NvidiaError("Unrecognized attribute name")

    monkeypatch.setattr("nvfan.installer.list_fan_map", fail_fan_map)
    monkeypatch.setattr("nvfan.installer.list_fans", lambda display: [0, 1, 2, 3, 4, 5])

    _apply_detected_hardware_config(config, ":1")

    text = config.read_text()
    assert "gpu_ids = [0, 1]" in text
    assert "fan_ids = [0, 1, 2, 3, 4, 5]" not in text
    assert "[fan_ids_by_gpu]" in text
    assert "0 = [0, 1, 2]" in text
    assert "1 = [3, 4, 5]" in text
