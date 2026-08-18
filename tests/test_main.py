import sys

import main


def test_self_check_funciona_sem_console(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "app.core.ffmpeg_finder.FFmpegFinder.ensure_available",
        lambda: tmp_path / "ffmpeg.exe",
    )
    monkeypatch.setattr(
        "app.core.transcriber.TranscriberWorker.device_description",
        lambda: "CPU de teste",
    )
    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(sys, "stderr", None)
    assert main.self_check() == 0
