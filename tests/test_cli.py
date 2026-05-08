import sys

from nvfan import __main__ as cli
from nvfan.nvidia import NvidiaError


def test_status_reports_nvidia_errors_without_traceback(monkeypatch, capsys):
    def fail_list_gpus():
        raise NvidiaError("Command not found: nvidia-smi")

    monkeypatch.setattr(sys, "argv", ["nv-fancurve", "status"])
    monkeypatch.setattr("nvfan.nvidia.list_gpus", fail_list_gpus)

    assert cli.main() == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "nv-fancurve: Command not found: nvidia-smi" in captured.err
    assert "Traceback" not in captured.err
