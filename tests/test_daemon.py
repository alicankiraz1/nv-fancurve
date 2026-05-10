from nvfan.config import Config, CurvePoint
from nvfan.daemon import FanDaemon
from nvfan.nvidia import GpuStats


def test_handle_gpu_sets_all_configured_fans(monkeypatch):
    calls = []
    cfg = Config(curve=[CurvePoint(50, 40), CurvePoint(80, 100)], fan_ids=[0, 1])
    daemon = FanDaemon(cfg)

    monkeypatch.setattr(
        "nvfan.daemon.query_stats",
        lambda gpu_id: GpuStats(
            gpu_id,
            temp=65,
            fan_speed=0,
            power_draw=250.0,
            clock_mhz=1800,
        ),
    )
    monkeypatch.setattr(
        "nvfan.daemon.set_fan_speeds",
        lambda gpu_id, fan_ids, speed_pct, display: calls.append(
            (gpu_id, fan_ids, speed_pct, display)
        ),
    )

    daemon._handle_gpu(0)

    assert calls == [(0, [0, 1], 70, ":1")]


def test_handle_gpu_uses_gpu_specific_fan_map(monkeypatch):
    calls = []
    cfg = Config(
        gpu_ids=[0, 1],
        fan_ids_by_gpu={0: [0, 1, 2], 1: [3, 4, 5]},
        curve=[CurvePoint(50, 40), CurvePoint(80, 100)],
    )
    daemon = FanDaemon(cfg)

    monkeypatch.setattr(
        "nvfan.daemon.query_stats",
        lambda gpu_id: GpuStats(
            gpu_id,
            temp=65,
            fan_speed=0,
            power_draw=250.0,
            clock_mhz=1800,
        ),
    )
    monkeypatch.setattr(
        "nvfan.daemon.set_fan_speeds",
        lambda gpu_id, fan_ids, speed_pct, display: calls.append(
            (gpu_id, fan_ids, speed_pct, display)
        ),
    )

    daemon._handle_gpu(0)
    daemon._handle_gpu(1)

    assert calls == [
        (0, [0, 1, 2], 70, ":1"),
        (1, [3, 4, 5], 70, ":1"),
    ]
