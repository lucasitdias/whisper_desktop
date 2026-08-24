import wave
from pathlib import Path
from types import SimpleNamespace

from PySide6.QtCore import QObject, Signal
from PySide6.QtMultimedia import QAudioFormat, QtAudio
from PySide6.QtTest import QSignalSpy

from app.core.recorder import (
    RECORDING_FORMATS,
    AudioEncodingWorker,
    RecorderController,
    RecordingState,
    _WaveSink,
)


def pcm_format() -> QAudioFormat:
    audio_format = QAudioFormat()
    audio_format.setSampleRate(48000)
    audio_format.setChannelCount(1)
    audio_format.setSampleFormat(QAudioFormat.SampleFormat.Int16)
    return audio_format


def test_wave_sink_grava_pcm_incremental_e_calcula_metricas(tmp_path: Path):
    destination = tmp_path / "captura.wav"
    sink = _WaveSink(destination, pcm_format())
    payload = (1000).to_bytes(2, "little", signed=True) * 48000
    assert sink.write(payload) == len(payload)
    assert sink.duration_seconds == 1
    assert 0 < sink.peak_level < 0.1
    assert sink.peak_dbfs is not None
    sink.finalize()

    with wave.open(str(destination), "rb") as recorded:
        assert recorded.getframerate() == 48000
        assert recorded.getnchannels() == 1
        assert recorded.getnframes() == 48000


def test_medidor_reflete_bloco_atual_sem_perder_pico_geral(tmp_path: Path):
    sink = _WaveSink(tmp_path / "nivel.wav", pcm_format())
    sink.write((30000).to_bytes(2, "little", signed=True) * 100)
    overall_peak = sink.peak_level
    sink.write((300).to_bytes(2, "little", signed=True) * 100)
    assert sink.current_peak_level < 0.02
    assert sink.peak_level == overall_peak
    sink.finalize()


def test_buffer_de_captura_tem_40_ms_e_quadros_completos():
    audio_format = pcm_format()
    audio_format.setChannelCount(2)
    assert RecorderController.capture_buffer_size(audio_format) == 7680


def test_primeiro_bloco_confirma_gravacao_e_nao_e_perdido(tmp_path: Path):
    class FakeInput:
        def readAll(self):
            return (1200).to_bytes(2, "little", signed=True) * 480

    controller = RecorderController()
    sink = _WaveSink(tmp_path / "inicio.wav", pcm_format())
    controller.state = RecordingState.STARTING
    controller._sink = sink
    controller._input_device = FakeInput()

    controller._read_audio()

    assert controller.state is RecordingState.RECORDING
    assert sink.frames_written == 480
    sink.finalize()


def test_pausa_mantem_fluxo_ativo_descarta_intervalo_e_retoma_sem_atraso(tmp_path: Path):
    class FakeInput:
        def __init__(self):
            self.payload = b""

        def readAll(self):
            payload, self.payload = self.payload, b""
            return payload

    class FakeSource:
        pass

    controller = RecorderController()
    sink = _WaveSink(tmp_path / "pausa.wav", pcm_format())
    input_device = FakeInput()
    controller.state = RecordingState.RECORDING
    controller._sink = sink
    controller._input_device = input_device
    controller._audio_source = FakeSource()

    input_device.payload = (1000).to_bytes(2, "little", signed=True) * 480
    controller._read_audio()
    controller.pause()
    input_device.payload = (0).to_bytes(2, "little", signed=True) * 4800
    controller._read_audio()
    controller.resume()
    input_device.payload = (2000).to_bytes(2, "little", signed=True) * 480
    controller._read_audio()

    assert controller.state is RecordingState.RECORDING
    assert sink.frames_written == 960
    assert sink.duration_seconds == 0.02
    sink.finalize()


def test_parar_desconecta_ready_read_antes_de_fechar_wav(monkeypatch, tmp_path: Path):
    class FakeInput(QObject):
        readyRead = Signal()

        def __init__(self):
            super().__init__()
            self.read_count = 0

        def readAll(self):
            self.read_count += 1
            return (1000).to_bytes(2, "little", signed=True) * 100

    class FakeSource:
        def __init__(self, input_device):
            self.input_device = input_device

        def stop(self):
            self.input_device.readyRead.emit()

    class FakeEncoder(QObject):
        completed = Signal(object)
        failed = Signal(str, object)
        finished = Signal()

        def __init__(self, *_args, **_kwargs):
            super().__init__()

        def start(self):
            return None

    controller = RecorderController()
    sink = _WaveSink(tmp_path / "captura.wav", pcm_format())
    input_device = FakeInput()
    input_device.readyRead.connect(controller._read_audio)
    controller.state = RecordingState.RECORDING
    controller._sink = sink
    controller._input_device = input_device
    controller._audio_source = FakeSource(input_device)
    controller._destination = tmp_path / "saida.mp3"
    controller._recording_format = RECORDING_FORMATS[0]
    controller._device_name = "Microfone"
    monkeypatch.setattr("app.core.recorder.AudioEncodingWorker", FakeEncoder)

    controller.stop()

    assert sink.closed
    assert input_device.read_count == 1


def test_timer_detecta_microfone_interrompido_sem_sinal_tipado():
    class FailedSource:
        def state(self):
            return QtAudio.State.StoppedState

        def error(self):
            return QtAudio.Error.OpenError

        def stop(self):
            return None

    controller = RecorderController()
    controller.state = RecordingState.RECORDING
    controller._audio_source = FailedSource()
    failed = QSignalSpy(controller.failed)

    controller._check_audio_state()

    assert failed.count() == 1
    assert "desconectado" in failed.at(0)[0]
    assert controller.state is RecordingState.READY


def test_formatos_de_saida_e_argumentos_ffmpeg():
    assert [item.label for item in RECORDING_FORMATS] == [
        "MP3 192 kbps",
        "MP3 320 kbps",
        "M4A AAC 256 kbps",
    ]
    assert RECORDING_FORMATS[0].ffmpeg_output_args() == [
        "-vn",
        "-c:a",
        "libmp3lame",
        "-b:a",
        "192k",
        "-f",
        "mp3",
    ]
    assert "+faststart" in RECORDING_FORMATS[2].ffmpeg_output_args()


def test_encoding_publica_atomicamente_apos_sucesso(monkeypatch, tmp_path: Path):
    wav_path = tmp_path / "captura.wav"
    wav_path.write_bytes(b"wav")
    destination = tmp_path / "gravacao.mp3"
    worker = AudioEncodingWorker(
        wav_path,
        destination,
        RECORDING_FORMATS[0],
        "Microfone de teste",
        1.0,
        -3.0,
        (),
    )

    monkeypatch.setattr(
        "app.core.recorder.FFmpegFinder.ensure_available", lambda: tmp_path / "ffmpeg.exe"
    )

    def fake_run(command, **_kwargs):
        Path(command[-1]).write_bytes(b"mp3")
        return SimpleNamespace(returncode=0, stderr="", stdout="")

    monkeypatch.setattr("app.core.recorder.subprocess.run", fake_run)
    completed = QSignalSpy(worker.completed)
    worker.run()

    assert completed.count() == 1
    result = completed.at(0)[0]
    assert result.final_path == destination.resolve()
    assert destination.read_bytes() == b"mp3"
    assert not list(tmp_path.glob("*.part.mp3"))


def test_encoding_preserva_wav_quando_ffmpeg_falha(monkeypatch, tmp_path: Path):
    wav_path = tmp_path / "captura.wav"
    wav_path.write_bytes(b"wav")
    worker = AudioEncodingWorker(
        wav_path,
        tmp_path / "gravacao.m4a",
        RECORDING_FORMATS[2],
        "Microfone",
        1.0,
        None,
        (),
    )
    monkeypatch.setattr(
        "app.core.recorder.FFmpegFinder.ensure_available", lambda: tmp_path / "ffmpeg.exe"
    )
    monkeypatch.setattr(
        "app.core.recorder.subprocess.run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=1, stderr="codec falhou", stdout=""),
    )
    failed = QSignalSpy(worker.failed)
    worker.run()

    assert failed.count() == 1
    assert "codec falhou" in failed.at(0)[0]
    assert wav_path.is_file()


def test_negocia_pcm_48khz_e_limita_dois_canais():
    preferred = pcm_format()
    preferred.setChannelCount(6)
    device = SimpleNamespace(
        preferredFormat=lambda: preferred,
        isFormatSupported=lambda candidate: (
            candidate.sampleRate() == 48000
            and candidate.channelCount() == 2
            and candidate.sampleFormat() is QAudioFormat.SampleFormat.Int16
        ),
    )
    selected = RecorderController.best_format(device)
    assert selected.sampleRate() == 48000
    assert selected.channelCount() == 2


def test_alertas_de_qualidade_e_estado_inicial():
    controller = RecorderController()
    assert controller.state is RecordingState.READY
    assert "baixo" in " ".join(controller.quality_warnings(0.02)).lower()
    assert "clipping" in " ".join(controller.quality_warnings(0.99)).lower()
    assert controller.quality_warnings(0.5) == ()
