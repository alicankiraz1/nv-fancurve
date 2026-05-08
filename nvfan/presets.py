"""Built-in fan curve presets shown by `nv-fancurve presets`."""

PRESETS = {
    "aggressive": {
        "description": "For 24/7 inference or training. Keeps GPU below about 75 C.",
        "curve": [
            (45, 30),
            (55, 40),
            (60, 50),
            (70, 65),
            (75, 75),
            (80, 85),
            (85, 100),
        ],
    },
    "balanced": {
        "description": "Reasonable default. Quiet at idle, ramps up under load.",
        "curve": [
            (50, 30),
            (60, 40),
            (70, 55),
            (75, 70),
            (82, 90),
            (88, 100),
        ],
    },
    "silent": {
        "description": "Prioritizes quiet operation. May allow 80 C+.",
        "curve": [
            (50, 25),
            (65, 35),
            (75, 50),
            (82, 75),
            (88, 100),
        ],
    },
}
