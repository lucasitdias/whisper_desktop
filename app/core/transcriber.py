"""Worker Qt responsável pela transcrição local com OpenAI Whisper."""

from __future__ import annotations

import contextlib
import gc
import io
import math
import os
import re
import threading
import time
import traceback
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from PySide6.QtCore import QThread, Signal

from .ffmpeg_finder import FFmpegFinder
from .model_catalog import (
    MODEL_BY_ID,
    ModelIntegrityError,
    ModelManager,
    ModelUnavailableError,
)

_torch_runtime: Any | None = None
_whisper_runtime: Any | None = None
_runtime_configured = False
_model_cache_lock = threading.RLock()
_cached_model: Any | None = None
_cached_model_key: tuple[str, str] | None = None


def _load_runtime() -> tuple[Any, Any]:
    """Importa os runtimes pesados somente dentro da transcrição/autodiagnóstico."""
    global _runtime_configured, _torch_runtime, _whisper_runtime
    if _torch_runtime is None:
        import torch as loaded_torch

        _torch_runtime = loaded_torch
    if _whisper_runtime is None:
        import whisper as loaded_whisper

        _whisper_runtime = loaded_whisper
    if not _runtime_configured:
        thread_count = max(1, min(8, os.cpu_count() or 1))
        _torch_runtime.set_num_threads(thread_count)
        with contextlib.suppress(RuntimeError):
            _torch_runtime.set_num_interop_threads(1)
        cuda_backend = getattr(_torch_runtime.backends, "cuda", None)
        if cuda_backend is not None and hasattr(cuda_backend, "matmul"):
            cuda_backend.matmul.allow_tf32 = True
        _runtime_configured = True
    return _torch_runtime, _whisper_runtime


@dataclass(frozen=True, slots=True)
class TranscriptionSegment:
    start: float
    end: float
    text: str
    average_logprob: float | None = None
    compression_ratio: float | None = None
    reviewed: bool = False
    suspected_hallucination: bool = False
    discarded_as_silence: bool = False


@dataclass(frozen=True, slots=True)
class TranscriptionWord:
    start: float
    end: float
    text: str
    probability: float


@dataclass(frozen=True, slots=True)
class TranscriptionResult:
    source_name: str
    duration_seconds: float
    processed_seconds: float
    text: str
    segments: tuple[TranscriptionSegment, ...]
    model_name: str
    language: str
    device: str
    transcribed_at: datetime
    average_word_confidence: float | None = None
    word_count: int = 0
    low_confidence_words: tuple[TranscriptionWord, ...] = ()
    reviewed_segment_count: int = 0
    suspected_hallucination_count: int = 0
    recording_device: str | None = None
    recording_format: str | None = None
    recording_peak_dbfs: float | None = None
    recording_warnings: tuple[str, ...] = ()
    processing_seconds: float | None = None
    discarded_silence_segment_count: int = 0

    @property
    def processing_coverage_percent(self) -> float:
        if self.duration_seconds <= 0:
            return 100.0
        return min(100.0, max(0.0, self.processed_seconds / self.duration_seconds * 100))

    @property
    def last_speech_end_seconds(self) -> float | None:
        ends = [segment.end for segment in self.segments if segment.text.strip()]
        return max(ends) if ends else None

    @property
    def low_confidence_word_count(self) -> int:
        return len(self.low_confidence_words)


class TranscriptionCancelled(Exception):
    """Interrupção solicitada pelo usuário, sem representar falha da aplicação."""


class TranscriptionPriority(StrEnum):
    """Prioridade de decodificação sem alterar o checkpoint selecionado."""

    FAST = "fast"
    BALANCED = "balanced"
    MAX_FIDELITY = "max_fidelity"


@dataclass(frozen=True, slots=True)
class DecodingProfile:
    """Parâmetros objetivos aplicados à busca e à revisão seletiva."""

    beam_size: int
    best_of: int
    patience: float | None
    review_beam_size: int
    review_margin_seconds: float


@dataclass(frozen=True, slots=True)
class TranscriptionOptions:
    """Opções explícitas de qualidade usadas por uma execução do Whisper."""

    model_name: str = "large-v3"
    language: str = "pt"
    initial_prompt: str = ""
    selective_review: bool = False
    priority: TranscriptionPriority = TranscriptionPriority.BALANCED

    MODEL_PARAMETERS = {
        model_id: spec.parameters for model_id, spec in MODEL_BY_ID.items()
    }

    def __post_init__(self) -> None:
        if self.model_name not in self.MODEL_PARAMETERS:
            raise ValueError("Selecione um perfil de transcrição válido.")
        normalized_prompt = self.initial_prompt.strip()
        if len(normalized_prompt) > 1000:
            raise ValueError("O contexto da transcrição deve ter no máximo 1.000 caracteres.")
        object.__setattr__(self, "initial_prompt", normalized_prompt)
        try:
            priority = TranscriptionPriority(self.priority)
        except ValueError as error:
            raise ValueError("Selecione uma prioridade de transcrição válida.") from error
        object.__setattr__(self, "priority", priority)

    @property
    def parameter_count(self) -> int:
        return self.MODEL_PARAMETERS[self.model_name]

    @property
    def effective_selective_review(self) -> bool:
        return self.selective_review or self.priority is TranscriptionPriority.MAX_FIDELITY

    @property
    def decoding_profile(self) -> DecodingProfile:
        if self.priority is TranscriptionPriority.FAST:
            beam_size = 1 if self.model_name in {"tiny", "base"} else 3
            return DecodingProfile(
                beam_size=beam_size,
                best_of=beam_size,
                patience=None,
                review_beam_size=8,
                review_margin_seconds=0.5,
            )
        if self.priority is TranscriptionPriority.MAX_FIDELITY:
            return DecodingProfile(
                beam_size=5,
                best_of=5,
                patience=1.2,
                review_beam_size=10,
                review_margin_seconds=0.75,
            )
        beam_size = MODEL_BY_ID[self.model_name].beam_size
        return DecodingProfile(
            beam_size=beam_size,
            best_of=beam_size,
            patience=None,
            review_beam_size=10,
            review_margin_seconds=0.5,
        )


_TIMESTAMP_PATTERN = re.compile(
    r"^\[(?P<start>(?:\d{2}:)?\d{2}:\d{2}(?:\.\d+)?)\s+--?>\s+"
    r"(?P<end>(?:\d{2}:)?\d{2}:\d{2}(?:\.\d+)?)\]\s*(?P<text>.*)$"
)


def _timestamp_to_seconds(value: str) -> float:
    parts = [float(part) for part in value.split(":")]
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    return parts[0] * 3600 + parts[1] * 60 + parts[2]


class _WhisperOutputStream(io.TextIOBase):
    """Converte a saída incremental do Whisper em sinais da interface."""

    def __init__(self, worker: TranscriberWorker, duration: float) -> None:
        self.worker = worker
        self.duration = max(duration, 0.001)
        self.buffer = ""

    def writable(self) -> bool:
        return True

    def write(self, text: str) -> int:
        self.worker._raise_if_cancelled()
        self.buffer += text
        while "\n" in self.buffer:
            line, self.buffer = self.buffer.split("\n", 1)
            self._process(line.strip())
        return len(text)

    def flush(self) -> None:
        if self.buffer.strip():
            self._process(self.buffer.strip())
            self.buffer = ""

    def _process(self, line: str) -> None:
        self.worker._raise_if_cancelled()
        match = _TIMESTAMP_PATTERN.match(line)
        if not match:
            return
        end = _timestamp_to_seconds(match.group("end"))
        segment_text = match.group("text").strip()
        if segment_text:
            self.worker.segment_decoded.emit(segment_text)
        percent = 20 + int(min(1.0, end / self.duration) * 75)
        self.worker.progress_changed.emit(min(95, percent))


class TranscriberWorker(QThread):
    """Executa toda a carga pesada fora da thread principal da GUI."""

    status_changed = Signal(str)
    progress_changed = Signal(int)
    segment_decoded = Signal(str)
    completed = Signal(object)
    failed = Signal(str)
    cancelled = Signal(str)
    device_detected = Signal(str, str)

    MODEL_NAME = "large-v3"
    LANGUAGE = "pt"
    MODEL_CACHE_IDLE_MS = 5 * 60 * 1000

    def __init__(
        self,
        audio_path: str | Path,
        parent: Any = None,
        *,
        options: TranscriptionOptions | None = None,
        public_source_name: str | None = None,
        recording_metadata: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(parent)
        self.audio_path = Path(audio_path)
        self.options = options or TranscriptionOptions()
        self.public_source_name = Path(public_source_name or self.audio_path.name).name
        self.recording_metadata = dict(recording_metadata or {})
        self._cancel_event = threading.Event()

    def cancel(self) -> None:
        """Solicita cancelamento cooperativo sem encerrar a thread à força."""
        if self._cancel_event.is_set():
            return
        self._cancel_event.set()
        self.requestInterruption()
        self.status_changed.emit(
            "Cancelamento solicitado; finalizando a etapa atual com segurança..."
        )

    def _raise_if_cancelled(self) -> None:
        if self._cancel_event.is_set() or self.isInterruptionRequested():
            raise TranscriptionCancelled

    @staticmethod
    def detect_device() -> str:
        torch, _whisper = _load_runtime()
        try:
            if torch.cuda.is_available():
                # O PyTorch expõe GPUs AMD/ROCm pela mesma API ``torch.cuda``.
                return "rocm" if getattr(torch.version, "hip", None) else "cuda"
        except (OSError, RuntimeError):
            # Um driver instalado, porém indisponível, não deve impedir o fallback.
            pass
        xpu = getattr(torch, "xpu", None)
        if xpu is not None:
            try:
                if xpu.is_available():
                    return "xpu"
            except (OSError, RuntimeError):
                pass
        return "cpu"

    @staticmethod
    def device_description(device: str | None = None) -> str:
        torch, _whisper = _load_runtime()
        device = device or TranscriberWorker.detect_device()
        try:
            if device == "cuda":
                return f"GPU NVIDIA CUDA: {torch.cuda.get_device_name(0)}"
            if device == "rocm":
                return f"GPU AMD ROCm: {torch.cuda.get_device_name(0)}"
            if device == "xpu":
                return f"GPU Intel XPU: {torch.xpu.get_device_name(0)}"
        except Exception:
            return TranscriberWorker._processing_name(device)
        return "CPU (aceleração por GPU não disponível)"

    @staticmethod
    def _processing_name(device: str) -> str:
        return {
            "cuda": "GPU NVIDIA CUDA",
            "rocm": "GPU AMD ROCm",
            "xpu": "GPU Intel XPU",
            "cpu": "CPU",
        }.get(device, device.upper())

    @staticmethod
    def runtime_description() -> str:
        """Identifica o runtime incorporado, mesmo quando não há GPU disponível."""
        torch, _whisper = _load_runtime()
        if getattr(torch.version, "hip", None):
            return f"AMD ROCm {torch.version.hip}"
        if getattr(torch.version, "cuda", None):
            return f"NVIDIA CUDA {torch.version.cuda}"
        if getattr(torch.version, "xpu", None):
            return f"Intel XPU {torch.version.xpu}"
        return "CPU"

    @staticmethod
    def _torch_device(device: str) -> str:
        # ROCm mantém compatibilidade com o nome de dispositivo ``cuda``.
        return "cuda" if device == "rocm" else device

    @staticmethod
    def _empty_device_cache(device: str) -> None:
        torch, _whisper = _load_runtime()
        if device in {"cuda", "rocm"}:
            torch.cuda.empty_cache()
        elif device == "xpu":
            torch.xpu.empty_cache()

    @classmethod
    def release_cached_model(cls) -> bool:
        """Libera o único modelo mantido após o uso para recuperar RAM e VRAM."""
        global _cached_model, _cached_model_key
        with _model_cache_lock:
            model = _cached_model
            key = _cached_model_key
            _cached_model = None
            _cached_model_key = None
        if model is None:
            return False
        device = key[1] if key is not None else "cpu"
        del model
        cls._empty_device_cache(device)
        gc.collect()
        return True

    def _load_cached_model(self, device: str) -> tuple[Any, bool]:
        """Carrega sob demanda e reutiliza o modelo nas transcrições seguintes."""
        global _cached_model, _cached_model_key
        _torch, whisper = _load_runtime()
        key = (self.options.model_name, device)
        with _model_cache_lock:
            if _cached_model is not None and _cached_model_key == key:
                self.status_changed.emit(
                    f"Modelo Whisper {self.options.model_name} já está pronto no cache."
                )
                return _cached_model, True

        # Nunca mantenha simultaneamente dois modelos grandes em RAM/VRAM.
        self.release_cached_model()
        spec = MODEL_BY_ID[self.options.model_name]
        self.status_changed.emit(
            f"Verificando o modelo Whisper {self.options.model_name} no armazenamento local..."
        )
        self.progress_changed.emit(16)
        checkpoint = ModelManager.require_checkpoint(
            spec,
            progress=lambda percent: self.progress_changed.emit(16 + round(percent * 0.02)),
            cancelled=lambda: self._cancel_event.is_set() or self.isInterruptionRequested(),
        )
        self.status_changed.emit(
            f"Carregando o modelo Whisper {self.options.model_name} do disco..."
        )
        model = whisper.load_model(
            str(checkpoint),
            device=self._torch_device(device),
            download_root=None,
            in_memory=False,
        )
        alignment_heads = getattr(whisper, "_ALIGNMENT_HEADS", {}).get(
            self.options.model_name
        )
        if alignment_heads is not None and hasattr(model, "set_alignment_heads"):
            model.set_alignment_heads(alignment_heads)
        with _model_cache_lock:
            _cached_model = model
            _cached_model_key = key
        return model, False

    @staticmethod
    def model_cache_root() -> Path:
        return ModelManager.cache_root()

    def run(self) -> None:
        audio: Any | None = None
        run_started = time.perf_counter()
        try:
            self._raise_if_cancelled()
            self._validate_input()
            self.status_changed.emit("Verificando o FFmpeg...")
            self.progress_changed.emit(-1)
            ffmpeg = FFmpegFinder.ensure_available()
            FFmpegFinder.prepend_to_path(ffmpeg)
            self._raise_if_cancelled()

            self.status_changed.emit("Preparando o mecanismo de transcrição...")
            self.progress_changed.emit(-1)
            _torch, whisper = _load_runtime()
            device = self.detect_device()
            processing = self.device_description(device)
            self.device_detected.emit(device, processing)
            self.status_changed.emit(f"Processamento confirmado: {processing}.")
            self._raise_if_cancelled()

            self.status_changed.emit("Decodificando o arquivo de áudio...")
            self.progress_changed.emit(5)
            audio = whisper.load_audio(str(self.audio_path))
            duration = float(len(audio) / whisper.audio.SAMPLE_RATE)
            self.progress_changed.emit(15)
            self._raise_if_cancelled()

            try:
                raw_result = self._transcribe(audio, duration, device)
            except Exception as error:
                if device == "cpu" or not self._is_accelerator_oom(error, device):
                    raise
                self.status_changed.emit(
                    "Memória da GPU insuficiente. Reiniciando automaticamente pela CPU..."
                )
                self.progress_changed.emit(15)
                self.release_cached_model()
                self._raise_if_cancelled()
                raw_result = self._transcribe(audio, duration, "cpu")
                device = "cpu"

            self._raise_if_cancelled()

            segments = tuple(
                TranscriptionSegment(
                    start=float(segment.get("start", 0.0)),
                    end=float(segment.get("end", 0.0)),
                    text=str(segment.get("text", "")).strip(),
                    average_logprob=self._finite_optional(segment.get("avg_logprob")),
                    compression_ratio=self._finite_optional(segment.get("compression_ratio")),
                    reviewed=bool(segment.get("reviewed", False)),
                    suspected_hallucination=self._is_suspected_hallucination(segment),
                    discarded_as_silence=bool(segment.get("discarded_as_silence", False)),
                )
                for segment in raw_result.get("segments", [])
            )
            words = self._words_with_confidence(raw_result)
            word_probabilities = [word.probability for word in words]
            average_confidence = (
                math.fsum(word_probabilities) / len(word_probabilities)
                if word_probabilities
                else None
            )
            result = TranscriptionResult(
                source_name=self.public_source_name,
                duration_seconds=duration,
                processed_seconds=duration,
                text=str(raw_result.get("text", "")).strip(),
                segments=segments,
                model_name=self.options.model_name,
                language=self.options.language,
                device=device,
                transcribed_at=datetime.now().astimezone(),
                average_word_confidence=average_confidence,
                word_count=len(word_probabilities),
                low_confidence_words=tuple(
                    word for word in words if word.probability < 0.5
                ),
                reviewed_segment_count=sum(segment.reviewed for segment in segments),
                suspected_hallucination_count=sum(
                    segment.suspected_hallucination and not segment.discarded_as_silence
                    for segment in segments
                ),
                discarded_silence_segment_count=int(
                    raw_result.get("discarded_silence_segment_count", 0)
                ),
                recording_device=self.recording_metadata.get("device"),
                recording_format=self.recording_metadata.get("format"),
                recording_peak_dbfs=self._finite_optional(
                    self.recording_metadata.get("peak_dbfs")
                ),
                recording_warnings=tuple(self.recording_metadata.get("warnings", ())),
                processing_seconds=time.perf_counter() - run_started,
            )
            self._raise_if_cancelled()
            self.status_changed.emit("Gerando o documento Markdown...")
            self.progress_changed.emit(98)
            self.completed.emit(result)
            self.progress_changed.emit(100)
            self.status_changed.emit("Transcrição concluída com sucesso.")
        except TranscriptionCancelled:
            message = "Transcrição cancelada. Nenhum resultado parcial foi salvo."
            self.progress_changed.emit(0)
            self.status_changed.emit(message)
            self.cancelled.emit(message)
        except Exception as error:
            traceback.print_exc()
            self.failed.emit(self._friendly_error(error))
        finally:
            audio = None
            gc.collect()

    def _transcribe(self, audio: Any, duration: float, device: str) -> dict[str, Any]:
        torch, whisper = _load_runtime()
        processing = self.device_description(device)
        if device in {"cuda", "rocm"}:
            with contextlib.suppress(Exception):
                torch.cuda.reset_peak_memory_stats()
        model, cache_hit = self._load_cached_model(device)
        try:
            self._raise_if_cancelled()
            self.status_changed.emit(
                f"Transcrevendo em Português do Brasil usando {processing}..."
            )
            self.progress_changed.emit(20)
            stream = _WhisperOutputStream(self, duration)
            profile = self.options.decoding_profile
            self.status_changed.emit(
                f"{processing} ativo — perfil {self.options.model_name}, "
                f"prioridade {self.options.priority.value}, busca {profile.beam_size}, "
                f"timestamps por palavra e modelo "
                f"{'reutilizado' if cache_hit else 'carregado'}."
            )
            decode_options: dict[str, Any] = {
                "language": self.options.language,
                "task": "transcribe",
                "verbose": True,
                "fp16": device != "cpu",
                "beam_size": profile.beam_size,
                "best_of": profile.best_of,
                "condition_on_previous_text": True,
                "word_timestamps": True,
                "hallucination_silence_threshold": 1.0,
                "initial_prompt": self.options.initial_prompt or None,
            }
            if profile.patience is not None:
                decode_options["patience"] = profile.patience
            with torch.inference_mode(), contextlib.redirect_stdout(stream):
                raw_result = model.transcribe(audio, **decode_options)
            if self.options.effective_selective_review:
                raw_result = self._review_low_confidence_segments(
                    model, audio, raw_result, device, profile
                )
            raw_result = self._discard_hypotheses_over_effective_silence(
                raw_result, audio, whisper.audio.SAMPLE_RATE
            )
            return raw_result
        finally:
            if "stream" in locals():
                stream.flush()
            if device in {"cuda", "rocm"}:
                with contextlib.suppress(Exception):
                    peak_mb = torch.cuda.max_memory_allocated() / (1024 * 1024)
                    self.status_changed.emit(
                        f"{processing} confirmado durante a inferência; "
                        f"pico alocado: {peak_mb:.0f} MB."
                    )
            # O modelo permanece pronto por poucos minutos. A interface possui um timer
            # de inatividade que recupera RAM/VRAM sem penalizar transcrições consecutivas.

    def _validate_input(self) -> None:
        if not self.audio_path.is_file():
            raise FileNotFoundError("O arquivo de áudio selecionado não existe.")
        if self.audio_path.suffix.lower() not in {".mp3", ".m4a", ".wav"}:
            raise ValueError("Selecione um arquivo MP3, M4A ou WAV interno válido.")

    def _review_low_confidence_segments(
        self,
        model: Any,
        audio: Any,
        raw_result: dict[str, Any],
        device: str,
        profile: DecodingProfile,
    ) -> dict[str, Any]:
        """Refaz somente trechos suspeitos e aceita uma hipótese mensuravelmente melhor."""

        segments = list(raw_result.get("segments", []))
        reviewed = 0
        _torch, whisper = _load_runtime()
        sample_rate = whisper.audio.SAMPLE_RATE
        for index, segment in enumerate(segments):
            self._raise_if_cancelled()
            if reviewed >= 12 or not self._segment_needs_review(segment):
                continue
            target_start = max(0.0, float(segment.get("start", 0.0)))
            target_end = max(target_start, float(segment.get("end", target_start)))
            if target_end - target_start < 0.25:
                continue
            audio_duration = len(audio) / sample_rate
            chunk_start = max(0.0, target_start - profile.review_margin_seconds)
            chunk_end = min(
                audio_duration, target_end + profile.review_margin_seconds
            )
            chunk = audio[
                int(chunk_start * sample_rate) : int(chunk_end * sample_rate)
            ]
            if len(chunk) == 0:
                continue
            self.status_changed.emit(
                f"Revisando trecho de baixa confiança {reviewed + 1}..."
            )
            candidate_result = model.transcribe(
                chunk,
                language=self.options.language,
                task="transcribe",
                verbose=False,
                fp16=device != "cpu",
                beam_size=profile.review_beam_size,
                best_of=profile.review_beam_size,
                patience=1.2,
                condition_on_previous_text=False,
                word_timestamps=True,
                hallucination_silence_threshold=1.0,
                initial_prompt=self.options.initial_prompt or None,
            )
            candidate_segments = candidate_result.get("segments") or []
            if not candidate_segments:
                continue
            candidate = self._merge_review_candidate(
                candidate_segments,
                chunk_start=chunk_start,
                target_start=target_start,
                target_end=target_end,
            )
            if self._candidate_is_better(segment, candidate):
                candidate["reviewed"] = True
                segments[index] = candidate
                reviewed += 1
        if reviewed:
            raw_result = dict(raw_result)
            raw_result["segments"] = segments
            raw_result["text"] = " ".join(
                str(segment.get("text", "")).strip()
                for segment in segments
                if str(segment.get("text", "")).strip()
            )
        return raw_result

    @classmethod
    def _segment_needs_review(cls, segment: dict[str, Any]) -> bool:
        probabilities = [
            float(word["probability"])
            for word in segment.get("words") or []
            if cls._finite_optional(word.get("probability")) is not None
        ]
        confidence = math.fsum(probabilities) / len(probabilities) if probabilities else 1.0
        logprob = cls._finite_optional(segment.get("avg_logprob"))
        compression = cls._finite_optional(segment.get("compression_ratio"))
        no_speech = cls._finite_optional(segment.get("no_speech_prob"))
        return (
            confidence < 0.55
            or (logprob is not None and logprob < -1.0)
            or (compression is not None and compression > 2.4)
            or (no_speech is not None and no_speech >= 0.8 and confidence < 0.65)
        )

    @classmethod
    def _is_suspected_hallucination(cls, segment: dict[str, Any]) -> bool:
        if segment.get("discarded_as_silence"):
            return True
        probabilities = [
            float(word["probability"])
            for word in segment.get("words") or []
            if cls._finite_optional(word.get("probability")) is not None
        ]
        confidence = math.fsum(probabilities) / len(probabilities) if probabilities else 0.0
        no_speech = cls._finite_optional(segment.get("no_speech_prob"))
        compression = cls._finite_optional(segment.get("compression_ratio"))
        return (
            no_speech is not None
            and no_speech >= 0.8
            and confidence < 0.65
            or compression is not None
            and compression > 2.4
        )

    @staticmethod
    def _discard_hypotheses_over_effective_silence(
        raw_result: dict[str, Any], audio: Any, sample_rate: int
    ) -> dict[str, Any]:
        """Descarta texto somente quando o intervalo é eletricamente quase silencioso.

        -72 dBFS fica muito abaixo de fala utilizável. A decisão é registrada no segmento e no
        relatório, portanto não é uma correção linguística nem uma alteração silenciosa.
        """
        silence_peak = 10 ** (-72.0 / 20.0)
        segments = [dict(segment) for segment in raw_result.get("segments", [])]
        discarded = 0
        for segment in segments:
            if not str(segment.get("text", "")).strip():
                continue
            start = max(0, int(float(segment.get("start", 0.0)) * sample_rate))
            end = min(
                len(audio),
                max(start + 1, int(float(segment.get("end", 0.0)) * sample_rate)),
            )
            chunk = audio[start:end]
            peak = float(abs(chunk).max()) if len(chunk) else 0.0
            if peak > silence_peak:
                continue
            segment["text"] = ""
            segment["words"] = []
            segment["discarded_as_silence"] = True
            discarded += 1
        if not discarded:
            return raw_result
        result = dict(raw_result)
        result["segments"] = segments
        result["text"] = " ".join(
            str(segment.get("text", "")).strip()
            for segment in segments
            if str(segment.get("text", "")).strip()
        )
        result["discarded_silence_segment_count"] = discarded
        return result

    @staticmethod
    def _merge_review_candidate(
        candidate_segments: list[dict[str, Any]],
        *,
        chunk_start: float,
        target_start: float,
        target_end: float,
    ) -> dict[str, Any]:
        words: list[dict[str, Any]] = []
        texts: list[str] = []
        logprobs: list[float] = []
        compression_ratios: list[float] = []
        for segment in candidate_segments:
            value = TranscriberWorker._finite_optional(segment.get("avg_logprob"))
            if value is not None:
                logprobs.append(value)
            value = TranscriberWorker._finite_optional(segment.get("compression_ratio"))
            if value is not None:
                compression_ratios.append(value)
            for word in segment.get("words") or []:
                absolute_start = chunk_start + float(word.get("start", 0.0))
                absolute_end = chunk_start + float(word.get("end", absolute_start))
                midpoint = (absolute_start + absolute_end) / 2
                if not target_start <= midpoint <= target_end:
                    continue
                adjusted = dict(word)
                adjusted["start"] = max(target_start, absolute_start)
                adjusted["end"] = min(target_end, absolute_end)
                words.append(adjusted)
                word_text = str(word.get("word", ""))
                if word_text:
                    texts.append(word_text)
        return {
            "start": target_start,
            "end": target_end,
            "text": "".join(texts).strip(),
            "words": words,
            "avg_logprob": max(logprobs) if logprobs else None,
            "compression_ratio": min(compression_ratios) if compression_ratios else None,
            "no_speech_prob": min(
                (
                    float(segment["no_speech_prob"])
                    for segment in candidate_segments
                    if TranscriberWorker._finite_optional(segment.get("no_speech_prob"))
                    is not None
                ),
                default=None,
            ),
        }

    @classmethod
    def _candidate_is_better(
        cls, original: dict[str, Any], candidate: dict[str, Any]
    ) -> bool:
        if not str(candidate.get("text", "")).strip():
            return False
        original_score = cls._segment_score(original)
        candidate_score = cls._segment_score(candidate)
        compression = cls._finite_optional(candidate.get("compression_ratio"))
        original_no_speech = cls._finite_optional(original.get("no_speech_prob"))
        candidate_no_speech = cls._finite_optional(candidate.get("no_speech_prob"))
        if candidate_no_speech is not None and candidate_no_speech >= 0.8:
            return False
        if (
            original_no_speech is not None
            and candidate_no_speech is not None
            and candidate_no_speech > original_no_speech + 0.05
        ):
            return False
        return candidate_score >= original_score + 0.05 and (
            compression is None or compression <= 2.4
        )

    @classmethod
    def _segment_score(cls, segment: dict[str, Any]) -> float:
        probabilities = [
            float(word["probability"])
            for word in segment.get("words") or []
            if cls._finite_optional(word.get("probability")) is not None
        ]
        if probabilities:
            return math.fsum(probabilities) / len(probabilities)
        logprob = cls._finite_optional(segment.get("avg_logprob"))
        return max(0.0, min(1.0, 1.0 + (logprob or -1.0)))

    @staticmethod
    def _finite_optional(value: Any) -> float | None:
        if isinstance(value, (int, float)) and math.isfinite(value):
            return float(value)
        return None

    @staticmethod
    def _is_cuda_oom(error: Exception) -> bool:
        return TranscriberWorker._is_accelerator_oom(error, "cuda")

    @staticmethod
    def _is_accelerator_oom(error: Exception, device: str) -> bool:
        torch, _whisper = _load_runtime()
        backend = torch.xpu if device == "xpu" else torch.cuda
        oom_type = getattr(backend, "OutOfMemoryError", RuntimeError)
        return isinstance(error, oom_type) or "out of memory" in str(error).lower()

    @staticmethod
    def _words_with_confidence(raw_result: dict[str, Any]) -> list[TranscriptionWord]:
        words: list[TranscriptionWord] = []
        for segment in raw_result.get("segments", []):
            for word in segment.get("words") or []:
                probability = word.get("probability")
                if isinstance(probability, (int, float)) and math.isfinite(probability):
                    words.append(
                        TranscriptionWord(
                            start=float(word.get("start", segment.get("start", 0.0))),
                            end=float(word.get("end", segment.get("end", 0.0))),
                            text=str(word.get("word", "")).strip(),
                            probability=min(1.0, max(0.0, float(probability))),
                        )
                    )
        return words

    @staticmethod
    def _friendly_error(error: Exception) -> str:
        if isinstance(
            error,
            (FileNotFoundError, ValueError, ModelUnavailableError, ModelIntegrityError),
        ):
            return str(error)
        message = str(error).strip() or error.__class__.__name__
        if "url" in message.lower() or "network" in message.lower():
            return "Não foi possível baixar os recursos necessários. Verifique sua conexão."
        return f"Falha durante a transcrição: {message}"
