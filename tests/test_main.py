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


def test_streams_windowed_sao_gravaveis(monkeypatch):
    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(sys, "stderr", None)

    main.ensure_standard_streams()

    assert sys.stdout is not None
    assert sys.stderr is not None
    assert sys.stdout.write("teste") == 5
    assert sys.stderr.write("erro") == 4


def test_self_check_grava_json(monkeypatch, tmp_path):
    destination = tmp_path / "diagnostico.json"
    monkeypatch.setattr(
        "app.core.ffmpeg_finder.FFmpegFinder.ensure_available",
        lambda: tmp_path / "ffmpeg.exe",
    )
    monkeypatch.setattr(
        "app.core.transcriber.TranscriberWorker.device_description",
        lambda: "GPU CUDA de teste",
    )

    assert main.self_check(destination) == 0
    assert '"status": "ok"' in destination.read_text(encoding="utf-8")
    assert "GPU CUDA de teste" in destination.read_text(encoding="utf-8")
