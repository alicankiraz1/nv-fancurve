from nvfan.installer import _apply_detected_fan_ids


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
