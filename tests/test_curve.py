import pytest

from nvfan.config import Config, CurvePoint


def make_config(points):
    return Config(curve=[CurvePoint(t, f) for t, f in points])


def test_below_first_point():
    cfg = make_config([(50, 30), (80, 100)])

    assert cfg.fan_for_temp(40) == 30


def test_above_last_point():
    cfg = make_config([(50, 30), (80, 100)])

    assert cfg.fan_for_temp(95) == 100


def test_exact_match():
    cfg = make_config([(50, 30), (80, 100)])

    assert cfg.fan_for_temp(50) == 30
    assert cfg.fan_for_temp(80) == 100


def test_linear_interpolation():
    cfg = make_config([(50, 30), (80, 100)])

    assert cfg.fan_for_temp(65) == 65


def test_three_point_curve():
    cfg = make_config([(40, 20), (70, 60), (90, 100)])

    assert cfg.fan_for_temp(40) == 20
    assert cfg.fan_for_temp(55) == 40
    assert cfg.fan_for_temp(80) == 80


def test_validation_rejects_out_of_range_points():
    with pytest.raises(ValueError, match="Invalid temp"):
        CurvePoint(temp=200, fan=50)
    with pytest.raises(ValueError, match="Invalid fan"):
        CurvePoint(temp=70, fan=150)


def test_empty_curve_cannot_calculate_fan():
    cfg = Config(curve=[])

    with pytest.raises(ValueError, match="Empty fan curve"):
        cfg.fan_for_temp(60)


def test_duplicate_temperatures_are_rejected():
    with pytest.raises(ValueError, match="duplicate"):
        make_config([(50, 30), (50, 40)])
