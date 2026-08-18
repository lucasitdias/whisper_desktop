"""Worker Qt responsável pela transcrição local com OpenAI Whisper."""

from __future__ import annotations

import contextlib
import gc
import io
import os
import re
import sys
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
class TranscriptionResult:
    source_name: str
    duration_seconds: float
    text: str
    segments: tuple[TranscriptionSegment, ...]
    model_name: str
    language: str
    device: str
    transcribed_at: datetime


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

    MODEL_NAME = "turbo"
    LANGUAGE = "pt"

    def __init__(self, audio_path: str | Path, parent: Any = None) -> None:
        super().__init__(parent)
        self.audio_path = Path(audio_path)

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
            self._validate_input()
            self.status_changed.emit("Verificando o FFmpeg...")
            self.progress_changed.emit(-1)
            ffmpeg = FFmpegFinder.ensure_available()
            FFmpegFinder.prepend_to_path(ffmpeg)

            self.status_changed.emit("Decodificando o arquivo de áudio...")
            self.progress_changed.emit(5)
            audio = whisper.load_audio(str(self.audio_path))
            duration = float(len(audio) / whisper.audio.SAMPLE_RATE)
            self.progress_changed.emit(15)

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
                raw_result = self._transcribe(audio, duration, "cpu")
                device = "cpu"

            segments = tuple(
                TranscriptionSegment(
                    start=float(segment.get("start", 0.0)),
                    end=float(segment.get("end", 0.0)),
                    text=str(segment.get("text", "")).strip(),
                )
                for segment in raw_result.get("segments", [])
            )
            result = TranscriptionResult(
                source_name=self.audio_path.name,
                duration_seconds=duration,
                text=str(raw_result.get("text", "")).strip(),
                segments=segments,
                model_name=self.MODEL_NAME,
                language=self.LANGUAGE,
                device=device,
                transcribed_at=datetime.now().astimezone(),
            )
            self.status_changed.emit("Gerando o documento Markdown...")
            self.progress_changed.emit(98)
            self.completed.emit(result)
            self.progress_changed.emit(100)
            self.status_changed.emit("Transcrição concluída com sucesso.")
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
        self.status_changed.emit(f"Transcrevendo em Português do Brasil usando {processing}...")
        self.progress_changed.emit(20)
        stream = _WhisperOutputStream(self, duration)
        try:
            with contextlib.redirect_stdout(stream):
                return model.transcribe(
                    audio,
                    language=self.LANGUAGE,
                    task="transcribe",
                    verbose=True,
                    fp16=device == "cuda",
                )
        finally:
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
    def _friendly_error(error: Exception) -> str:
        if isinstance(error, (FileNotFoundError, ValueError)):
            return str(error)
        message = str(error).strip() or error.__class__.__name__
        if "url" in message.lower() or "network" in message.lower():
            return "Não foi possível baixar os recursos necessários. Verifique sua conexão."
        return f"Falha durante a transcrição: {message}"
