"""Worker Qt responsável pela transcrição local com OpenAI Whisper."""

from __future__ import annotations

import contextlib
import gc
import io
import math
import os
import re
import sys
import threading
import traceback
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import torch
import whisper
from PySide6.QtCore import QThread, Signal

from .ffmpeg_finder import FFmpegFinder


@dataclass(frozen=True, slots=True)
class TranscriptionSegment:
    start: float
    end: float
    text: str


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

    MODEL_NAME = "turbo"
    LANGUAGE = "pt"

    def __init__(self, audio_path: str | Path, parent: Any = None) -> None:
        super().__init__(parent)
        self.audio_path = Path(audio_path)
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
        return "cuda" if torch.cuda.is_available() else "cpu"

    @staticmethod
    def device_description() -> str:
        if torch.cuda.is_available():
            try:
                return f"GPU CUDA: {torch.cuda.get_device_name(0)}"
            except Exception:
                return "GPU CUDA disponível"
        return "CPU (CUDA não disponível)"

    @staticmethod
    def model_cache_root() -> Path:
        if sys.platform.startswith("win"):
            base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        else:
            base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
        return base / "WhisperTranscriber" / "models"

    def run(self) -> None:
        try:
            self._raise_if_cancelled()
            self._validate_input()
            self.status_changed.emit("Verificando o FFmpeg...")
            self.progress_changed.emit(-1)
            ffmpeg = FFmpegFinder.ensure_available()
            FFmpegFinder.prepend_to_path(ffmpeg)
            self._raise_if_cancelled()

            self.status_changed.emit("Decodificando o arquivo de áudio...")
            self.progress_changed.emit(5)
            audio = whisper.load_audio(str(self.audio_path))
            duration = float(len(audio) / whisper.audio.SAMPLE_RATE)
            self.progress_changed.emit(15)
            self._raise_if_cancelled()

            device = self.detect_device()
            try:
                raw_result = self._transcribe(audio, duration, device)
            except Exception as error:
                if device != "cuda" or not self._is_cuda_oom(error):
                    raise
                self.status_changed.emit(
                    "Memória da GPU insuficiente. Reiniciando automaticamente pela CPU..."
                )
                self.progress_changed.emit(15)
                torch.cuda.empty_cache()
                gc.collect()
                self._raise_if_cancelled()
                raw_result = self._transcribe(audio, duration, "cpu")
                device = "cpu"

            self._raise_if_cancelled()

            segments = tuple(
                TranscriptionSegment(
                    start=float(segment.get("start", 0.0)),
                    end=float(segment.get("end", 0.0)),
                    text=str(segment.get("text", "")).strip(),
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
                source_name=self.audio_path.name,
                duration_seconds=duration,
                processed_seconds=duration,
                text=str(raw_result.get("text", "")).strip(),
                segments=segments,
                model_name=self.MODEL_NAME,
                language=self.LANGUAGE,
                device=device,
                transcribed_at=datetime.now().astimezone(),
                average_word_confidence=average_confidence,
                word_count=len(word_probabilities),
                low_confidence_words=tuple(
                    word for word in words if word.probability < 0.5
                ),
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

    def _transcribe(self, audio: Any, duration: float, device: str) -> dict[str, Any]:
        processing = "GPU CUDA" if device == "cuda" else "CPU"
        self.status_changed.emit(f"Carregando o modelo Whisper turbo em {processing}...")
        self.progress_changed.emit(-1)
        model = whisper.load_model(
            self.MODEL_NAME,
            device=device,
            download_root=str(self.model_cache_root()),
        )
        try:
            self._raise_if_cancelled()
            self.status_changed.emit(
                f"Transcrevendo em Português do Brasil usando {processing}..."
            )
            self.progress_changed.emit(20)
            stream = _WhisperOutputStream(self, duration)
            with contextlib.redirect_stdout(stream):
                return model.transcribe(
                    audio,
                    language=self.LANGUAGE,
                    task="transcribe",
                    verbose=True,
                    fp16=device == "cuda",
                    word_timestamps=True,
                )
        finally:
            if "stream" in locals():
                stream.flush()
            del model
            if device == "cuda":
                torch.cuda.empty_cache()

    def _validate_input(self) -> None:
        if not self.audio_path.is_file():
            raise FileNotFoundError("O arquivo de áudio selecionado não existe.")
        if self.audio_path.suffix.lower() not in {".mp3", ".m4a"}:
            raise ValueError("Selecione um arquivo MP3 ou M4A válido.")

    @staticmethod
    def _is_cuda_oom(error: Exception) -> bool:
        oom_type = getattr(torch.cuda, "OutOfMemoryError", RuntimeError)
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
        if isinstance(error, (FileNotFoundError, ValueError)):
            return str(error)
        message = str(error).strip() or error.__class__.__name__
        if "url" in message.lower() or "network" in message.lower():
            return "Não foi possível baixar os recursos necessários. Verifique sua conexão."
        return f"Falha durante a transcrição: {message}"
