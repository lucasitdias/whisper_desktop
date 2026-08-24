import json
from pathlib import Path

import pytest

from scripts import benchmark_accuracy
from scripts.benchmark_accuracy import edit_distance, error_rate, load_manifest, normalize


def test_normalizacao_e_metricas_de_erro():
    assert normalize("  Olá, MUNDO! ") == "olá mundo"
    assert edit_distance(["um", "teste"], ["um", "texto"]) == 1
    assert error_rate("um teste", "um texto") == 0.5
    assert error_rate("abc", "adc", characters=True) == pytest.approx(1 / 3)


def test_manifesto_resolve_audio_relativo(tmp_path: Path):
    audio = tmp_path / "amostra.mp3"
    audio.write_bytes(b"audio")
    manifest = tmp_path / "amostras.jsonl"
    manifest.write_text(
        json.dumps({"audio": audio.name, "reference": "Texto correto"}) + "\n",
        encoding="utf-8",
    )
    entries = load_manifest(manifest)
    assert entries[0]["audio"] == audio.resolve()


def test_manifesto_rejeita_entrada_sem_referencia(tmp_path: Path):
    manifest = tmp_path / "amostras.jsonl"
    manifest.write_text('{"audio":"ausente.mp3"}\n', encoding="utf-8")
    with pytest.raises(ValueError):
        load_manifest(manifest)


def test_benchmark_reutiliza_pipeline_local_sem_download(monkeypatch, tmp_path: Path):
    audio = tmp_path / "amostra.wav"
    audio.write_bytes(b"wav")
    calls: list[tuple[str, str, bool, float, str]] = []

    monkeypatch.setattr(
        benchmark_accuracy.FFmpegFinder,
        "ensure_available",
        staticmethod(lambda: tmp_path / "ffmpeg"),
    )
    monkeypatch.setattr(
        benchmark_accuracy.FFmpegFinder,
        "prepend_to_path",
        staticmethod(lambda _path: None),
    )
    monkeypatch.setattr(
        benchmark_accuracy.TranscriberWorker,
        "detect_device",
        staticmethod(lambda: "cpu"),
    )
    monkeypatch.setattr(
        benchmark_accuracy.TranscriberWorker,
        "release_cached_model",
        classmethod(lambda cls: True),
    )
    monkeypatch.setattr(
        benchmark_accuracy.whisper,
        "load_audio",
        lambda _path: [0.0] * benchmark_accuracy.whisper.audio.SAMPLE_RATE,
    )

    def fake_transcribe(worker, _audio, duration, device):
        calls.append(
            (
                worker.options.model_name,
                worker.options.priority.value,
                worker.options.effective_selective_review,
                duration,
                device,
            )
        )
        return {"text": "texto correto", "segments": []}

    monkeypatch.setattr(
        benchmark_accuracy.TranscriberWorker, "_transcribe", fake_transcribe
    )

    report = benchmark_accuracy.benchmark(
        [{"audio": audio, "reference": "texto correto", "context": "termo"}],
        ["turbo"],
        include_review=True,
    )

    assert calls == [
        ("turbo", "balanced", False, 1.0, "cpu"),
        ("turbo", "balanced", True, 1.0, "cpu"),
    ]
    assert report["summary"]["turbo:balanced:baseline"]["wer"] == 0
    assert report["summary"]["turbo:balanced:review"]["cer"] == 0
