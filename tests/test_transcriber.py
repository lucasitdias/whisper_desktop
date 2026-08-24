from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from PySide6.QtTest import QSignalSpy

from app.core import transcriber as transcriber_module
from app.core.transcriber import (
    TranscriberWorker,
    TranscriptionCancelled,
    TranscriptionOptions,
    TranscriptionPriority,
    _WhisperOutputStream,
)

torch, whisper = transcriber_module._load_runtime()


@pytest.fixture(autouse=True)
def clear_cached_model_between_tests():
    TranscriberWorker.release_cached_model()
    yield
    TranscriberWorker.release_cached_model()


@pytest.fixture(autouse=True)
def local_checkpoint_without_gigabyte_io(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(
        transcriber_module.ModelManager,
        "require_checkpoint",
        lambda spec, **_kwargs: tmp_path / spec.filename,
    )


def prepare_worker(monkeypatch, tmp_path: Path) -> TranscriberWorker:
    audio_path = tmp_path / "audio.mp3"
    audio_path.write_bytes(b"audio")
    monkeypatch.setattr(
        "app.core.transcriber.FFmpegFinder.ensure_available", lambda: tmp_path / "ffmpeg"
    )
    monkeypatch.setattr("app.core.transcriber.FFmpegFinder.prepend_to_path", lambda _path: None)
    monkeypatch.setattr(whisper, "load_audio", lambda _path: np.zeros(16000))
    monkeypatch.setattr(whisper.audio, "SAMPLE_RATE", 16000)
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
    monkeypatch.setattr(torch.cuda, "empty_cache", lambda: None)
    completed = QSignalSpy(worker.completed)
    worker.run()
    assert calls == ["cuda", "cpu"]
    assert completed.at(0)[0].device == "cpu"


def test_detecta_cuda_nvidia_com_prioridade(monkeypatch):
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    monkeypatch.setattr(torch.version, "hip", None, raising=False)
    monkeypatch.setattr(
        torch.cuda, "get_device_name", lambda _index: "GPU NVIDIA"
    )

    assert TranscriberWorker.detect_device() == "cuda"
    assert TranscriberWorker.device_description() == "GPU NVIDIA CUDA: GPU NVIDIA"


def test_detecta_rocm_amd(monkeypatch):
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    monkeypatch.setattr(torch.version, "hip", "7.2", raising=False)
    monkeypatch.setattr(
        torch.cuda, "get_device_name", lambda _index: "GPU AMD"
    )

    assert TranscriberWorker.detect_device() == "rocm"
    assert TranscriberWorker.device_description() == "GPU AMD ROCm: GPU AMD"


def test_detecta_xpu_intel_quando_cuda_indisponivel(monkeypatch):
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    fake_xpu = SimpleNamespace(
        is_available=lambda: True,
        get_device_name=lambda _index: "GPU Intel",
        empty_cache=lambda: None,
        OutOfMemoryError=RuntimeError,
    )
    monkeypatch.setattr(torch, "xpu", fake_xpu, raising=False)

    assert TranscriberWorker.detect_device() == "xpu"
    assert TranscriberWorker.device_description() == "GPU Intel XPU: GPU Intel"


def test_detecta_cpu_sem_backend_de_gpu(monkeypatch):
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    monkeypatch.setattr(
        torch,
        "xpu",
        SimpleNamespace(is_available=lambda: False),
        raising=False,
    )

    assert TranscriberWorker.detect_device() == "cpu"
    assert TranscriberWorker.device_description() == (
        "CPU (aceleração por GPU não disponível)"
    )


def test_driver_cuda_com_erro_faz_fallback_para_cpu(monkeypatch):
    def unavailable():
        raise RuntimeError("driver incompatível")

    monkeypatch.setattr(torch.cuda, "is_available", unavailable)
    monkeypatch.setattr(
        torch,
        "xpu",
        SimpleNamespace(is_available=lambda: False),
        raising=False,
    )

    assert TranscriberWorker.detect_device() == "cpu"


def test_descreve_runtime_cuda_mesmo_sem_gpu(monkeypatch):
    monkeypatch.setattr(torch.version, "hip", None, raising=False)
    monkeypatch.setattr(torch.version, "cuda", "13.0", raising=False)
    monkeypatch.setattr(torch.version, "xpu", None, raising=False)

    assert TranscriberWorker.runtime_description() == "NVIDIA CUDA 13.0"


@pytest.mark.parametrize(
    ("backend", "torch_device", "fp16"),
    [
        ("cuda", "cuda", True),
        ("rocm", "cuda", True),
        ("xpu", "xpu", True),
        ("cpu", "cpu", False),
    ],
)
def test_transcribe_usa_backend_e_parametros_de_qualidade(
    monkeypatch, tmp_path: Path, backend: str, torch_device: str, fp16: bool
):
    worker = TranscriberWorker(tmp_path / "audio.mp3")
    captured = {}

    class FakeModel:
        def transcribe(self, _audio, **options):
            captured["options"] = options
            return {"text": "ok", "segments": []}

    def fake_load_model(_name, *, device, download_root, in_memory):
        captured["checkpoint"] = Path(_name).name
        captured["device"] = device
        captured["download_root"] = download_root
        captured["in_memory"] = in_memory
        return FakeModel()

    monkeypatch.setattr(whisper, "load_model", fake_load_model)
    monkeypatch.setattr(worker, "_empty_device_cache", lambda _device: None)

    result = worker._transcribe(np.zeros(16000), 1.0, backend)

    assert result["text"] == "ok"
    assert captured["device"] == torch_device
    assert captured["checkpoint"] == "large-v3.pt"
    assert captured["download_root"] is None
    assert captured["in_memory"] is False
    assert captured["options"] == {
        "language": "pt",
        "task": "transcribe",
        "verbose": True,
        "fp16": fp16,
        "beam_size": 5,
        "best_of": 5,
        "condition_on_previous_text": True,
        "word_timestamps": True,
        "hallucination_silence_threshold": 1.0,
        "initial_prompt": None,
    }


def test_turbo_preserva_busca_de_alta_fidelidade_gpu_e_timestamps(monkeypatch, tmp_path: Path):
    worker = TranscriberWorker(
        tmp_path / "audio.mp3", options=TranscriptionOptions(model_name="turbo")
    )
    captured = {}

    class FakeModel:
        def transcribe(self, _audio, **options):
            captured.update(options)
            return {"text": "ok", "segments": []}

    monkeypatch.setattr(
        whisper,
        "load_model",
        lambda *_args, **_kwargs: FakeModel(),
    )
    monkeypatch.setattr(worker, "_empty_device_cache", lambda _device: None)

    worker._transcribe(np.zeros(16000), 1.0, "cuda")

    assert captured["fp16"] is True
    assert captured["beam_size"] == 3
    assert captured["best_of"] == 3
    assert captured["word_timestamps"] is True
    assert captured["hallucination_silence_threshold"] == 1.0


def test_turbo_maior_fidelidade_amplia_busca_paciencia_e_forca_revisao(
    monkeypatch, tmp_path: Path
):
    options = TranscriptionOptions(
        model_name="turbo",
        priority=TranscriptionPriority.MAX_FIDELITY,
    )
    worker = TranscriberWorker(tmp_path / "audio.mp3", options=options)
    calls: list[dict] = []

    class FakeModel:
        def transcribe(self, _audio, **decode_options):
            calls.append(decode_options)
            return {"text": "ok", "segments": []}

    monkeypatch.setattr(whisper, "load_model", lambda *_args, **_kwargs: FakeModel())
    monkeypatch.setattr(worker, "_empty_device_cache", lambda _device: None)

    worker._transcribe(np.zeros(16000), 1.0, "cuda")

    assert options.effective_selective_review
    assert calls[0]["beam_size"] == 5
    assert calls[0]["best_of"] == 5
    assert calls[0]["patience"] == 1.2


def test_perfil_rapido_adapta_busca_ao_tamanho_do_modelo():
    tiny = TranscriptionOptions(
        model_name="tiny", priority=TranscriptionPriority.FAST
    ).decoding_profile
    turbo = TranscriptionOptions(
        model_name="turbo", priority=TranscriptionPriority.FAST
    ).decoding_profile

    assert tiny.beam_size == 1
    assert turbo.beam_size == 3
    assert tiny.patience is None


@pytest.mark.parametrize("model_name", ["tiny", "base", "small", "medium", "turbo", "large-v3"])
def test_maior_fidelidade_e_consistente_nos_seis_modelos(model_name: str):
    options = TranscriptionOptions(
        model_name=model_name,
        priority=TranscriptionPriority.MAX_FIDELITY,
    )

    assert options.decoding_profile.beam_size == 5
    assert options.decoding_profile.patience == 1.2
    assert options.decoding_profile.review_beam_size == 10
    assert options.effective_selective_review


def test_modelo_e_reutilizado_entre_transcricoes_consecutivas(monkeypatch, tmp_path: Path):
    calls = []

    class FakeModel:
        def transcribe(self, _audio, **_options):
            return {"text": "ok", "segments": []}

    def fake_load_model(*_args, **_kwargs):
        calls.append("load")
        return FakeModel()

    monkeypatch.setattr(whisper, "load_model", fake_load_model)
    monkeypatch.setattr(TranscriberWorker, "_empty_device_cache", lambda _device: None)
    first = TranscriberWorker(tmp_path / "primeiro.mp3")
    second = TranscriberWorker(tmp_path / "segundo.mp3")

    first._transcribe(np.zeros(16000), 1.0, "cuda")
    second._transcribe(np.zeros(16000), 1.0, "cuda")

    assert calls == ["load"]
    assert TranscriberWorker.release_cached_model()
    assert not TranscriberWorker.release_cached_model()


def test_opcoes_de_maxima_precisao_e_contexto():
    options = TranscriptionOptions(initial_prompt="  OpenAI, PySide6  ")
    assert options.model_name == "large-v3"
    assert options.initial_prompt == "OpenAI, PySide6"
    assert options.parameter_count == 1_550_000_000


@pytest.mark.parametrize(
    ("model_name", "parameters"),
    [
        ("tiny", 39_000_000),
        ("base", 74_000_000),
        ("small", 244_000_000),
        ("medium", 769_000_000),
        ("turbo", 809_000_000),
        ("large-v3", 1_550_000_000),
    ],
)
def test_opcoes_catalogam_os_seis_modelos(model_name: str, parameters: int):
    options = TranscriptionOptions(model_name=model_name)
    assert options.parameter_count == parameters


def test_carregamento_por_caminho_restaura_alignment_heads(monkeypatch, tmp_path: Path):
    worker = TranscriberWorker(tmp_path / "audio.mp3")
    received = []

    class FakeModel:
        def set_alignment_heads(self, heads):
            received.append(heads)

        def transcribe(self, _audio, **_options):
            return {"text": "ok", "segments": []}

    monkeypatch.setattr(whisper, "_ALIGNMENT_HEADS", {"large-v3": "heads"})
    monkeypatch.setattr(whisper, "load_model", lambda *_args, **_kwargs: FakeModel())
    monkeypatch.setattr(worker, "_empty_device_cache", lambda _device: None)

    worker._transcribe(np.zeros(16000), 1.0, "cpu")

    assert received == ["heads"]


def test_opcoes_rejeitam_modelo_e_contexto_invalidos():
    with pytest.raises(ValueError):
        TranscriptionOptions(model_name="modelo-inexistente")
    with pytest.raises(ValueError):
        TranscriptionOptions(initial_prompt="x" * 1001)
    with pytest.raises(ValueError):
        TranscriptionOptions(priority="inexistente")


def test_revisao_seletiva_substitui_apenas_candidato_melhor():
    original = {
        "text": "termo errado",
        "avg_logprob": -1.2,
        "compression_ratio": 1.1,
        "words": [{"word": "erro", "probability": 0.3}],
    }
    candidate = {
        "text": "termo correto",
        "avg_logprob": -0.1,
        "compression_ratio": 1.0,
        "words": [{"word": "correto", "probability": 0.9}],
    }
    assert TranscriberWorker._segment_needs_review(original)
    assert TranscriberWorker._candidate_is_better(original, candidate)
    assert not TranscriberWorker._candidate_is_better(candidate, original)


def test_revisao_com_margem_descarta_palavras_fora_do_trecho_alvo():
    candidate = TranscriberWorker._merge_review_candidate(
        [
            {
                "avg_logprob": -0.1,
                "compression_ratio": 1.0,
                "no_speech_prob": 0.1,
                "words": [
                    {"word": " antes", "start": 0.0, "end": 0.4, "probability": 0.9},
                    {"word": " fala", "start": 0.8, "end": 1.2, "probability": 0.9},
                    {"word": " depois", "start": 1.8, "end": 2.2, "probability": 0.9},
                ],
            }
        ],
        chunk_start=9.25,
        target_start=10.0,
        target_end=11.0,
    )

    assert candidate["text"] == "fala"
    assert [word["word"].strip() for word in candidate["words"]] == ["fala"]
    assert candidate["start"] == 10.0
    assert candidate["end"] == 11.0


def test_revisao_nao_aceita_candidato_provavel_em_silencio():
    original = {
        "text": "fala original",
        "no_speech_prob": 0.3,
        "words": [{"word": "fala", "probability": 0.4}],
    }
    hallucinated = {
        "text": "Se inscreva no canal.",
        "no_speech_prob": 0.91,
        "words": [{"word": "canal", "probability": 0.95}],
    }
    assert not TranscriberWorker._candidate_is_better(original, hallucinated)


def test_destaca_alucinacao_provavel_sem_apagar_texto():
    segment = {
        "text": "Tchau.",
        "no_speech_prob": 0.87,
        "compression_ratio": 0.4,
        "words": [{"word": "Tchau.", "probability": 0.52}],
    }
    assert TranscriberWorker._is_suspected_hallucination(segment)
    assert TranscriberWorker._segment_needs_review(segment)


def test_descarta_hipotese_somente_sobre_silencio_eletrico():
    raw = {
        "text": "Obrigado.",
        "segments": [{"start": 0.0, "end": 1.0, "text": "Obrigado."}],
    }
    result = TranscriberWorker._discard_hypotheses_over_effective_silence(
        raw, np.zeros(16000), 16000
    )
    assert result["text"] == ""
    assert result["discarded_silence_segment_count"] == 1
    assert result["segments"][0]["discarded_as_silence"] is True


def test_preserva_fala_baixa_acima_do_limiar_eletrico():
    raw = {
        "text": "fala baixa",
        "segments": [{"start": 0.0, "end": 1.0, "text": "fala baixa"}],
    }
    result = TranscriberWorker._discard_hypotheses_over_effective_silence(
        raw, np.full(16000, 0.001), 16000
    )
    assert result is raw


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
