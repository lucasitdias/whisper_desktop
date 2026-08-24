"""Captura de microfone em PCM e conversão local segura com FFmpeg."""

from __future__ import annotations

import array
import contextlib
import math
import os
import shutil
import subprocess
import sys
import tempfile
import wave
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from PySide6.QtCore import QIODevice, QObject, QThread, QTimer, Signal
from PySide6.QtMultimedia import QAudioDevice, QAudioFormat, QAudioSource, QtAudio

from .ffmpeg_finder import FFmpegFinder


class RecordingState(StrEnum):
    READY = "ready"
    STARTING = "starting"
    RECORDING = "recording"
    PAUSED = "paused"
    FINALIZING = "finalizing"


@dataclass(frozen=True, slots=True)
class RecordingFormat:
    key: str
    label: str
    extension: str
    codec: str
    bitrate: str
    muxer: str

    def ffmpeg_output_args(self) -> list[str]:
        args = ["-vn", "-c:a", self.codec, "-b:a", self.bitrate]
        if self.extension == ".m4a":
            args.extend(["-movflags", "+faststart"])
        args.extend(["-f", self.muxer])
        return args


RECORDING_FORMATS: tuple[RecordingFormat, ...] = (
    RecordingFormat("mp3-192", "MP3 192 kbps", ".mp3", "libmp3lame", "192k", "mp3"),
    RecordingFormat("mp3-320", "MP3 320 kbps", ".mp3", "libmp3lame", "320k", "mp3"),
    RecordingFormat("m4a-256", "M4A AAC 256 kbps", ".m4a", "aac", "256k", "ipod"),
)


@dataclass(frozen=True, slots=True)
class RecordingResult:
    final_path: Path
    transcription_path: Path
    device_name: str
    duration_seconds: float
    recording_format: RecordingFormat
    peak_dbfs: float | None
    warnings: tuple[str, ...]

    @property
    def transcription_metadata(self) -> dict[str, Any]:
        return {
            "device": self.device_name,
            "format": self.recording_format.label,
            "peak_dbfs": self.peak_dbfs,
            "warnings": self.warnings,
        }


class _WaveSink:
    """Escritor Python de WAV PCM incremental com medição de pico."""

    def __init__(
        self, path: Path, audio_format: QAudioFormat
    ) -> None:
        self.path = path
        self.audio_format = audio_format
        self.frames_written = 0
        self.peak_sample = 0
        self.current_peak_sample = 0
        self.write_error: OSError | None = None
        self._wave = wave.open(str(path), "wb")  # noqa: SIM115 - fechado em finalize()
        self._wave.setnchannels(audio_format.channelCount())
        self._wave.setsampwidth(2)
        self._wave.setframerate(audio_format.sampleRate())
        self.closed = False

    def write(self, data: bytes | bytearray | memoryview) -> int:
        payload = bytes(data)
        if not payload:
            return 0
        try:
            self._wave.writeframesraw(payload)
        except OSError as error:
            self.write_error = error
            return -1
        samples = array.array("h")
        samples.frombytes(payload[: len(payload) - (len(payload) % 2)])
        if sys.byteorder != "little":
            samples.byteswap()
        highest = max(samples, default=0)
        lowest = min(samples, default=0)
        self.current_peak_sample = max(highest, -lowest)
        if self.current_peak_sample:
            self.peak_sample = max(self.peak_sample, self.current_peak_sample)
        frame_size = max(1, self.audio_format.bytesPerFrame())
        self.frames_written += len(payload) // frame_size
        return len(payload)

    @property
    def duration_seconds(self) -> float:
        return self.frames_written / max(1, self.audio_format.sampleRate())

    @property
    def peak_level(self) -> float:
        return min(1.0, self.peak_sample / 32767) if self.peak_sample else 0.0

    @property
    def current_peak_level(self) -> float:
        """Nível do bloco mais recente, usado pelo medidor em tempo real."""
        return (
            min(1.0, self.current_peak_sample / 32767)
            if self.current_peak_sample
            else 0.0
        )

    def consume_current_peak_level(self) -> float:
        """Retorna o pico mais recente e zera a janela do medidor."""
        level = self.current_peak_level
        self.current_peak_sample = 0
        return level

    @property
    def peak_dbfs(self) -> float | None:
        return 20 * math.log10(self.peak_level) if self.peak_level > 0 else None

    def finalize(self) -> None:
        if not self.closed:
            self._wave.close()
            self.closed = True


class AudioEncodingWorker(QThread):
    """Converte o WAV em segundo plano e publica o destino somente após sucesso."""

    completed = Signal(object)
    failed = Signal(str, object)

    def __init__(
        self,
        wav_path: Path,
        destination: Path,
        recording_format: RecordingFormat,
        device_name: str,
        duration_seconds: float,
        peak_dbfs: float | None,
        warnings: tuple[str, ...],
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.wav_path = wav_path
        self.destination = destination
        self.recording_format = recording_format
        self.device_name = device_name
        self.duration_seconds = duration_seconds
        self.peak_dbfs = peak_dbfs
        self.warnings = warnings

    def command(self, ffmpeg: Path, temporary_output: Path) -> list[str]:
        return [
            str(ffmpeg),
            "-hide_banner",
            "-loglevel",
            "error",
            "-nostdin",
            "-y",
            "-i",
            str(self.wav_path),
            *self.recording_format.ffmpeg_output_args(),
            str(temporary_output),
        ]

    def run(self) -> None:
        temporary_output = self.destination.with_name(
            f".{self.destination.stem}.part{self.recording_format.extension}"
        )
        try:
            ffmpeg = FFmpegFinder.ensure_available()
            self.destination.parent.mkdir(parents=True, exist_ok=True)
            temporary_output.unlink(missing_ok=True)
            result = subprocess.run(
                self.command(ffmpeg, temporary_output),
                check=False,
                capture_output=True,
                text=True,
                timeout=None,
                creationflags=(
                    subprocess.CREATE_NO_WINDOW if sys.platform.startswith("win") else 0
                ),
            )
            if result.returncode != 0 or not temporary_output.is_file():
                detail = (result.stderr or result.stdout).strip()
                raise OSError(detail or "O FFmpeg não gerou o arquivo de áudio.")
            if temporary_output.stat().st_size == 0:
                raise OSError("O FFmpeg gerou um arquivo vazio.")
            os.replace(temporary_output, self.destination)
            self.completed.emit(
                RecordingResult(
                    final_path=self.destination.resolve(),
                    transcription_path=self.wav_path.resolve(),
                    device_name=self.device_name,
                    duration_seconds=self.duration_seconds,
                    recording_format=self.recording_format,
                    peak_dbfs=self.peak_dbfs,
                    warnings=self.warnings,
                )
            )
        except Exception as error:
            temporary_output.unlink(missing_ok=True)
            self.failed.emit(f"Não foi possível finalizar a gravação: {error}", self.wav_path)


class RecorderController(QObject):
    """Máquina de estados da captura; deve ser usada na thread principal do Qt."""

    state_changed = Signal(object)
    elapsed_changed = Signal(float)
    level_changed = Signal(float)
    completed = Signal(object)
    failed = Signal(str, object)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.state = RecordingState.READY
        self._audio_source: QAudioSource | None = None
        self._input_device: QIODevice | None = None
        self._sink: _WaveSink | None = None
        self._encoder: AudioEncodingWorker | None = None
        self._temporary_root: Path | None = None
        self._destination: Path | None = None
        self._recording_format: RecordingFormat | None = None
        self._device_name = ""
        self._intentional_stop = False
        self._reading_audio = False
        self._timer = QTimer(self)
        self._timer.setInterval(50)
        self._timer.timeout.connect(self._publish_metrics)

    @staticmethod
    def best_format(device: QAudioDevice) -> QAudioFormat:
        preferred = device.preferredFormat()
        preferred_channels = max(1, min(2, preferred.channelCount()))
        rates = list(dict.fromkeys([48000, 44100, 16000, preferred.sampleRate()]))
        channels = list(dict.fromkeys([preferred_channels, 1, 2]))
        for rate in rates:
            for channel_count in channels:
                candidate = QAudioFormat()
                candidate.setSampleRate(rate)
                candidate.setChannelCount(channel_count)
                candidate.setSampleFormat(QAudioFormat.SampleFormat.Int16)
                if device.isFormatSupported(candidate):
                    return candidate
        raise ValueError(
            "O microfone não oferece PCM de 16 bits compatível. Atualize o driver ou escolha "
            "outro dispositivo de entrada."
        )

    @staticmethod
    def capture_buffer_size(audio_format: QAudioFormat, latency_ms: int = 40) -> int:
        """Calcula uma dica de buffer curta e alinhada a quadros PCM completos."""
        frame_size = max(1, audio_format.bytesPerFrame())
        frames = max(1, audio_format.sampleRate() * latency_ms // 1000)
        return frames * frame_size

    def start(
        self,
        device: QAudioDevice,
        destination: str | Path | None,
        recording_format: RecordingFormat,
    ) -> None:
        if self.state is not RecordingState.READY:
            raise RuntimeError("Já existe uma gravação em andamento.")
        if device.isNull():
            raise ValueError("Nenhum microfone válido foi selecionado.")
        self._cleanup_temporary()
        audio_format = self.best_format(device)
        self._temporary_root = Path(tempfile.mkdtemp(prefix="whisper-recording-"))
        destination_path = (
            Path(destination).expanduser()
            if destination is not None
            else self._temporary_root / f"gravacao{recording_format.extension}"
        )
        if destination_path.suffix.lower() != recording_format.extension:
            destination_path = destination_path.with_suffix(recording_format.extension)
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        wav_path = self._temporary_root / "captura-sem-perdas.wav"
        try:
            self._sink = _WaveSink(wav_path, audio_format)
            self._audio_source = QAudioSource(device, audio_format, self)
            # O backend pode ajustar esta dica ao mínimo seguro do hardware. Um buffer
            # curto evita blocos atrasados sem fazer polling ou acumular áudio em RAM.
            self._audio_source.setBufferSize(self.capture_buffer_size(audio_format))
            self._destination = destination_path
            self._recording_format = recording_format
            self._device_name = device.description()
            self._intentional_stop = False
            self._input_device = self._audio_source.start()
            if self._input_device is None:
                raise OSError("O sistema não abriu o fluxo do microfone selecionado.")
            self._input_device.readyRead.connect(self._read_audio)
            self._set_state(RecordingState.STARTING)
            self._timer.start()
        except Exception:
            if self._audio_source is not None:
                self._audio_source.stop()
            if self._sink is not None:
                self._sink.finalize()
            self._audio_source = None
            self._input_device = None
            self._sink = None
            self._cleanup_temporary()
            raise

    def pause(self) -> None:
        if self.state is not RecordingState.RECORDING or self._audio_source is None:
            return
        # Mantém o endpoint ativo e descarta os blocos durante a pausa. Suspender o
        # dispositivo pode exigir uma nova inicialização no Windows/Linux e causar
        # atraso ou inserir áudio antigo acumulado ao retomar.
        self._read_audio()
        self._set_state(RecordingState.PAUSED)
        self.level_changed.emit(0.0)

    def resume(self) -> None:
        if self.state is not RecordingState.PAUSED or self._audio_source is None:
            return
        # Elimina qualquer bloco que chegou antes do clique em Retomar.
        self._read_audio()
        self._set_state(RecordingState.RECORDING)

    def stop(self) -> None:
        if self.state not in {
            RecordingState.STARTING,
            RecordingState.RECORDING,
            RecordingState.PAUSED,
        }:
            return
        was_paused = self.state is RecordingState.PAUSED
        self._intentional_stop = True
        self._set_state(RecordingState.FINALIZING)
        self._timer.stop()
        if self._input_device is not None:
            with contextlib.suppress(RuntimeError, TypeError):
                self._input_device.readyRead.disconnect(self._read_audio)
        if was_paused and self._input_device is not None:
            # Nunca inclui no WAV um bloco que pertença ao intervalo pausado.
            bytes(self._input_device.readAll())
        else:
            self._read_audio()
        self._input_device = None
        if self._audio_source is not None:
            self._audio_source.stop()
        if self._sink is None:
            self._fail("A captura de áudio foi encerrada sem dados recuperáveis.")
            return
        self._sink.finalize()
        if self._sink.write_error is not None:
            self._fail(f"Falha ao gravar no disco: {self._sink.write_error}")
            return
        if self._sink.frames_written == 0:
            self._fail("Nenhum áudio foi capturado. Verifique o microfone e tente novamente.")
            return
        warnings = self.quality_warnings(self._sink.peak_level)
        self._encoder = AudioEncodingWorker(
            self._sink.path,
            self._destination,
            self._recording_format,
            self._device_name,
            self._sink.duration_seconds,
            self._sink.peak_dbfs,
            warnings,
            self,
        )
        self._encoder.completed.connect(self._encoding_completed)
        self._encoder.failed.connect(self._encoding_failed)
        self._encoder.finished.connect(self._encoder.deleteLater)
        self._encoder.start()

    @staticmethod
    def quality_warnings(peak_level: float) -> tuple[str, ...]:
        warnings: list[str] = []
        if peak_level <= 0.01:
            warnings.append("Sinal muito baixo; aproxime o microfone ou aumente o ganho.")
        elif peak_level < 0.05:
            warnings.append("Sinal baixo; a precisão pode ser reduzida.")
        if peak_level >= 0.98:
            warnings.append("Possível clipping; reduza o ganho ou afaste o microfone.")
        return tuple(warnings)

    def _publish_metrics(self) -> None:
        self._check_audio_state()
        if self._sink is None:
            return
        self.elapsed_changed.emit(self._sink.duration_seconds)
        self.level_changed.emit(self._sink.consume_current_peak_level())
        if self._sink.write_error is not None:
            self.stop()

    def _read_audio(self) -> None:
        if self._input_device is None or self._sink is None or self._reading_audio:
            return
        self._reading_audio = True
        try:
            payload = bytes(self._input_device.readAll())
            if not payload or self._sink.closed:
                return
            if self.state is RecordingState.PAUSED:
                return
            if self._sink.write(payload) < 0:
                return
            if self.state is RecordingState.STARTING:
                self._set_state(RecordingState.RECORDING)
        finally:
            self._reading_audio = False

    def _check_audio_state(self) -> None:
        state = self._audio_source.state() if self._audio_source is not None else None
        if (
            state == QtAudio.State.StoppedState
            and not self._intentional_stop
            and self.state
            in {
                RecordingState.STARTING,
                RecordingState.RECORDING,
                RecordingState.PAUSED,
            }
            and self._audio_source is not None
            and self._audio_source.error() != QtAudio.Error.NoError
        ):
            self._fail("O microfone foi desconectado ou deixou de responder.")

    def _encoding_completed(self, result: RecordingResult) -> None:
        self._encoder = None
        self._audio_source = None
        self._input_device = None
        self._sink = None
        self._set_state(RecordingState.READY)
        self.completed.emit(result)

    def _encoding_failed(self, message: str, recovery_path: object) -> None:
        self._encoder = None
        self._set_state(RecordingState.READY)
        self.failed.emit(message, recovery_path)

    def _fail(self, message: str) -> None:
        self._timer.stop()
        if self._audio_source is not None:
            self._intentional_stop = True
            self._audio_source.stop()
        self._input_device = None
        if self._sink is not None:
            self._sink.finalize()
        recovery = self._sink.path if self._sink and self._sink.path.is_file() else None
        self._audio_source = None
        self._sink = None
        self._set_state(RecordingState.READY)
        self.failed.emit(message, recovery)

    def _set_state(self, state: RecordingState) -> None:
        self.state = state
        self.state_changed.emit(state)

    def release_temporary(self, path: str | Path | None) -> None:
        if path is None:
            return
        candidate = Path(path).resolve()
        if self._temporary_root and candidate.parent == self._temporary_root.resolve():
            self._cleanup_temporary()

    def discard_cached_recording(self) -> None:
        """Remove a sessão temporária somente quando ela não estiver mais em uso."""
        if self.state is RecordingState.READY and self._encoder is None:
            self._cleanup_temporary()

    def _cleanup_temporary(self) -> None:
        if self._temporary_root:
            shutil.rmtree(self._temporary_root, ignore_errors=True)
        self._temporary_root = None
