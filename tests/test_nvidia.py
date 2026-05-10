from nvfan import nvidia


def test_list_fans_parses_nvidia_settings_output(monkeypatch):
    def fake_run(cmd, env=None, timeout=10):
        assert cmd == ["nvidia-settings", "-q", "fans"]
        assert env["DISPLAY"] == ":1"
        return "  Attribute 'fans' (host:1): 2.\n    [fan:0]\n    [fan:1]\n"

    monkeypatch.setattr(nvidia, "_run", fake_run)

    assert nvidia.list_fans(":1") == [0, 1]


def test_list_fans_can_query_one_gpu(monkeypatch):
    def fake_run(cmd, env=None, timeout=10):
        assert cmd == ["nvidia-settings", "-q", "[gpu:1]/fans"]
        assert env["DISPLAY"] == ":1"
        return "  Attribute 'fans' (host:1[gpu:1]): 3.\n    [fan:3]\n    [fan:4]\n"

    monkeypatch.setattr(nvidia, "_run", fake_run)

    assert nvidia.list_fans(":1", gpu_id=1) == [3, 4]


def test_list_fans_returns_unique_sorted_ids(monkeypatch):
    monkeypatch.setattr(
        nvidia,
        "_run",
        lambda cmd, env=None, timeout=10: "[fan:1]\n[fan:0]\n[fan:1]\n",
    )

    assert nvidia.list_fans(":1") == [0, 1]


def test_list_fan_map_queries_each_gpu(monkeypatch):
    calls = []

    def fake_list_fans(display, gpu_id=None):
        calls.append((display, gpu_id))
        return {0: [0, 1, 2], 1: [3, 4, 5]}[gpu_id]

    monkeypatch.setattr(nvidia, "list_fans", fake_list_fans)

    assert nvidia.list_fan_map([0, 1], ":1") == {0: [0, 1, 2], 1: [3, 4, 5]}
    assert calls == [(":1", 0), (":1", 1)]


def test_set_fan_speeds_sets_every_fan(monkeypatch):
    calls = []

    def fake_run(cmd, env=None, timeout=10):
        calls.append((cmd, env))
        return ""

    monkeypatch.setattr(nvidia, "_run", fake_run)

    nvidia.set_fan_speeds(0, [0, 1], 65, ":1")

    assert calls[0][0] == [
        "nvidia-settings",
        "-a",
        "[gpu:0]/GPUFanControlState=1",
        "-a",
        "[fan:0]/GPUTargetFanSpeed=65",
        "-a",
        "[fan:1]/GPUTargetFanSpeed=65",
    ]
    assert calls[0][1]["DISPLAY"] == ":1"
