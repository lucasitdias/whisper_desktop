from pathlib import Path

import numpy as np
import pytest
from PySide6.QtTest import QSignalSpy

from app.core.transcriber import (
    TranscriberWorker,
    TranscriptionCancelled,
    _WhisperOutputStream,
)


def prepare_worker(monkeypatch, tmp_path: Path) -> TranscriberWorker:
    audio_path = tmp_path / "audio.mp3"
    audio_path.write_bytes(b"audio")
    monkeypatch.setattr(
        "app.core.transcriber.FFmpegFinder.ensure_available", lambda: tmp_path / "ffmpeg"
    )
    monkeypatch.setattr("app.core.transcriber.FFmpegFinder.prepend_to_path", lambda _path: None)
    monkeypatch.setattr("app.core.transcriber.whisper.load_audio", lambda _path: np.zeros(16000))
    monkeypatch.setattr("app.core.transcriber.whisper.audio.SAMPLE_RATE", 16000)
    return TranscriberWorker(audio_path)


def test_worker_emite_resultado_cpu(monkeypatch, tmp_path: Path):
    worker = prepare_worker(monkeypatch, tmp_path)
    monkeypatch.setattr(worker, "detect_device", lambda: "cpu")
    monkeypatch.setattr(
        worker,
        "_transcribe",
        lambda *_args: {
            "text": " teste",
            "segments": [
                {
                    "start": 0,
                    "end": 1,
                    "text": " teste",
                    "words": [{"word": " teste", "probability": 0.9}],
                }
            ],
        },
    )
    completed = QSignalSpy(worker.completed)
    worker.run()
    assert completed.count() == 1
    result = completed.at(0)[0]
    assert result.text == "teste"
    assert result.device == "cpu"
    assert result.duration_seconds == 1
    assert result.processed_seconds == 1
    assert result.processing_coverage_percent == 100
    assert result.average_word_confidence == 0.9
    assert result.word_count == 1


def test_worker_faz_fallback_de_cuda_para_cpu(monkeypatch, tmp_path: Path):
    worker = prepare_worker(monkeypatch, tmp_path)
    monkeypatch.setattr(worker, "detect_device", lambda: "cuda")
    calls = []

    def transcribe(_audio, _duration, device):
        calls.append(device)
        if device == "cuda":
            raise RuntimeError("CUDA out of memory")
        return {"text": "ok", "segments": []}

    monkeypatch.setattr(worker, "_transcribe", transcribe)
    monkeypatch.setattr("app.core.transcriber.torch.cuda.empty_cache", lambda: None)
    completed = QSignalSpy(worker.completed)
    worker.run()
    assert calls == ["cuda", "cpu"]
    assert completed.at(0)[0].device == "cpu"


def test_stream_emite_segmento_e_progresso():
    worker = TranscriberWorker("audio.mp3")
    segments = QSignalSpy(worker.segment_decoded)
    progress = QSignalSpy(worker.progress_changed)
    stream = _WhisperOutputStream(worker, duration=10)
    stream.write("[00:00.000 --> 00:05.000] metade\n")
    assert segments.at(0)[0] == "metade"
    assert progress.at(0)[0] == 57


def test_worker_rejeita_arquivo_inexistente(tmp_path: Path):
    worker = TranscriberWorker(tmp_path / "ausente.mp3")
    failed = QSignalSpy(worker.failed)
    worker.run()
    assert failed.count() == 1
    assert "não existe" in failed.at(0)[0]


def test_worker_cancela_sem_emitir_falha_ou_resultado(monkeypatch, tmp_path: Path):
    worker = prepare_worker(monkeypatch, tmp_path)
    cancelled = QSignalSpy(worker.cancelled)
    failed = QSignalSpy(worker.failed)
    completed = QSignalSpy(worker.completed)

    worker.cancel()
    worker.run()

    assert cancelled.count() == 1
    assert "cancelada" in cancelled.at(0)[0].lower()
    assert failed.count() == 0
    assert completed.count() == 0


def test_stream_interrompe_inferencia_quando_cancelado():
    worker = TranscriberWorker("audio.mp3")
    stream = _WhisperOutputStream(worker, duration=10)
    worker.cancel()

    with pytest.raises(TranscriptionCancelled):
        stream.write("[00:00.000 --> 00:05.000] trecho\n")
