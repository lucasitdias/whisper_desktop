import subprocess
import sys
from pathlib import Path

import pytest
from PySide6.QtCore import QThread, Signal
from PySide6.QtMultimedia import QMediaPlayer

from app.core.model_catalog import ModelAvailability
from app.core.recorder import RECORDING_FORMATS, RecordingResult
from app.core.transcriber import TranscriptionPriority
from app.ui.main_window import DropZoneWidget, MainWindow


@pytest.fixture(autouse=True)
def modelos_disponiveis_sem_io(monkeypatch):
    monkeypatch.setattr(
        "app.ui.main_window.ModelManager.availability",
        lambda _spec: ModelAvailability.CACHED,
    )


def test_selecao_valida_habilita_transcricao(qtbot, tmp_path: Path):
    audio = tmp_path / "AUDIO.MP3"
    audio.write_bytes(b"audio")
    window = MainWindow()
    qtbot.addWidget(window)
    assert window.set_selected_file(str(audio)) is True
    assert window.transcribe_button.isEnabled()
    assert window.drop_zone.file_label.text() == "AUDIO.MP3"


def test_editor_atualiza_previa_e_copia(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.source_editor.setPlainText("# Título\n\nConteúdo")
    qtbot.waitUntil(lambda: "Título" in window.preview.toPlainText())
    window.copy_markdown()
    assert window.source_editor.toPlainText() == "# Título\n\nConteúdo"
    assert window.status_label.text().startswith("Markdown copiado")


def test_salvar_com_nome_sugerido(qtbot, monkeypatch, tmp_path: Path):
    audio = tmp_path / "aula.m4a"
    audio.write_bytes(b"audio")
    destination = tmp_path / "saida"
    window = MainWindow()
    qtbot.addWidget(window)
    window.set_selected_file(str(audio))
    window.source_editor.setPlainText("# Resultado")
    monkeypatch.setattr(
        "app.ui.main_window.QFileDialog.getSaveFileName",
        lambda *_args, **_kwargs: (str(destination), "Markdown (*.md)"),
    )
    window.save_markdown()
    assert (tmp_path / "saida.md").read_text(encoding="utf-8") == "# Resultado"


def test_start_da_thread_nao_bloqueia_interface(qtbot, monkeypatch, tmp_path: Path):
    audio = tmp_path / "audio.mp3"
    audio.write_bytes(b"audio")

    class SlowWorker(QThread):
        status_changed = Signal(str)
        progress_changed = Signal(int)
        segment_decoded = Signal(str)
        completed = Signal(object)
        failed = Signal(str)
        cancelled = Signal(str)

        def __init__(self, _path, parent=None, **_kwargs):
            super().__init__(parent)

        @staticmethod
        def device_description():
            return "CPU de teste"

        def run(self):
            self.msleep(80)

        def cancel(self):
            self.requestInterruption()

    monkeypatch.setattr("app.ui.main_window.TranscriberWorker", SlowWorker)
    window = MainWindow()
    qtbot.addWidget(window)
    window.set_selected_file(str(audio))
    window.start_transcription()
    assert window.worker is not None
    qtbot.waitUntil(lambda: window.worker is None, timeout=1000)


def test_extensoes_aceitas():
    assert DropZoneWidget.is_supported("arquivo.mp3")
    assert DropZoneWidget.is_supported("arquivo.M4A")
    assert not DropZoneWidget.is_supported("arquivo.wav")


def test_botao_cancela_transcricao_e_restaura_interface(qtbot, monkeypatch, tmp_path: Path):
    audio = tmp_path / "audio.mp3"
    audio.write_bytes(b"audio")

    class CancellableWorker(QThread):
        status_changed = Signal(str)
        progress_changed = Signal(int)
        segment_decoded = Signal(str)
        completed = Signal(object)
        failed = Signal(str)
        cancelled = Signal(str)

        def __init__(self, _path, parent=None, **_kwargs):
            super().__init__(parent)

        @staticmethod
        def device_description():
            return "CPU de teste"

        def run(self):
            while not self.isInterruptionRequested():
                self.msleep(5)

        def cancel(self):
            self.requestInterruption()
            self.cancelled.emit("Transcrição cancelada para teste.")

    monkeypatch.setattr("app.ui.main_window.TranscriberWorker", CancellableWorker)
    window = MainWindow()
    qtbot.addWidget(window)
    window.set_selected_file(str(audio))
    window.start_transcription()

    assert window.cancel_button.isEnabled()
    assert not window.transcribe_button.isEnabled()
    assert not window.drop_zone.isEnabled()

    window.cancel_button.click()
    qtbot.waitUntil(lambda: window.worker is None, timeout=1000)

    assert "cancelada" in window.status_label.text().lower()
    assert not window.cancel_button.isEnabled()
    assert window.transcribe_button.isEnabled()
    assert window.drop_zone.isEnabled()


def test_perfil_padrao_e_contexto_limitado(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    assert window.model_combo.currentData() == "large-v3"
    assert window.context_input.maxLength() == 1000
    assert not window.selective_review_checkbox.isChecked()
    assert window.priority_combo.currentData() == TranscriptionPriority.BALANCED.value


def test_modelos_exibem_nome_claro_e_ajuda_no_hover(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    assert window.model_combo.count() == 6
    assert (
        window.model_combo.currentText()
        == "Requer download — large-v3 — máxima fidelidade"
    )
    assert "vram" in window.model_combo.toolTip().lower()
    window.model_combo.setCurrentIndex(window.model_combo.findData("turbo"))
    assert window.model_combo.currentText() == "Offline — turbo — rápido e preciso"
    assert "809m" in window.model_combo.toolTip().lower()


def test_prioridade_de_fidelidade_ativa_revisao_e_bloqueia_desmarcacao(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.priority_combo.setCurrentIndex(
        window.priority_combo.findData(TranscriptionPriority.MAX_FIDELITY.value)
    )

    assert window.selective_review_checkbox.isChecked()
    assert not window.selective_review_checkbox.isEnabled()
    options = window._transcription_options()
    assert options.priority is TranscriptionPriority.MAX_FIDELITY
    assert options.effective_selective_review


def test_modelo_nao_disponivel_exige_download_e_bloqueia_transcricao(
    qtbot, monkeypatch, tmp_path: Path
):
    audio = tmp_path / "audio.mp3"
    audio.write_bytes(b"audio")
    window = MainWindow()
    qtbot.addWidget(window)
    window.model_combo.setCurrentIndex(window.model_combo.findData("tiny"))
    monkeypatch.setattr(
        "app.ui.main_window.ModelManager.availability",
        lambda _spec: ModelAvailability.DOWNLOAD_REQUIRED,
    )
    window._update_model_state()
    window.set_selected_file(str(audio))

    assert window.model_download_button.isEnabled()
    assert not window.transcribe_button.isEnabled()
    assert "depois funcionará offline" in window.model_status_label.text()


def test_large_v3_padrao_exige_download_quando_nao_esta_no_cache(
    qtbot, monkeypatch, tmp_path: Path
):
    audio = tmp_path / "audio.mp3"
    audio.write_bytes(b"audio")
    monkeypatch.setattr(
        "app.ui.main_window.ModelManager.availability",
        lambda _spec: ModelAvailability.DOWNLOAD_REQUIRED,
    )
    window = MainWindow()
    qtbot.addWidget(window)
    window.set_selected_file(str(audio))

    assert window.model_combo.currentData() == "large-v3"
    assert window.model_download_button.isEnabled()
    assert not window.transcribe_button.isEnabled()
    assert "2.9 GB" in window.model_status_label.text()


def test_expandir_resultado_preserva_texto_aba_e_restaura_com_escape(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window.source_editor.setPlainText("texto editado")
    window.tabs.setCurrentIndex(1)
    original_sizes = window.main_splitter.sizes()

    window.toggle_result_focus()

    assert not window.top_scroll.isVisible()
    assert window.result_panel.isVisibleTo(window)
    assert window.expand_result_button.text() == "Restaurar"
    assert window.source_editor.toPlainText() == "texto editado"
    assert window.tabs.currentIndex() == 1

    window._escape_focus_shortcut.activated.emit()

    assert not window._result_focus
    assert window.expand_result_button.text() == "Expandir resultado"
    assert window.main_splitter.sizes() == original_sizes
    assert window.source_editor.toPlainText() == "texto editado"


@pytest.mark.parametrize("width", [820, 900, 1240, 1536])
def test_layout_responsivo_nao_habilita_rolagem_horizontal(qtbot, width):
    window = MainWindow()
    qtbot.addWidget(window)
    window.resize(width, 760)
    window.show()
    qtbot.wait(20)
    assert window.top_scroll.horizontalScrollBar().maximum() == 0


def test_monitor_exibe_tempo_cpu_ram_gpu_e_vram(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)
    window._handle_processing_device("cpu", "CPU de teste")
    window._update_telemetry()
    text = window.telemetry_label.text()
    assert "Tempo:" in text
    assert "CPU do app:" in text
    assert "RAM do app:" in text
    assert "GPU: não utilizada" in text
    assert "VRAM:" in text


def test_player_usa_textos_e_icones_padrao_sem_glifos_quebrados(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    window._update_player_button(QMediaPlayer.PlaybackState.PlayingState)
    assert window.player_button.text() == "Pausar"
    assert not window.player_button.icon().isNull()

    window._update_player_button(QMediaPlayer.PlaybackState.StoppedState)
    assert window.player_button.text() == "Reproduzir"
    assert not window.player_button.icon().isNull()


def test_progresso_de_preparacao_permanece_determinado(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    window._handle_progress(-1)

    assert window.progress_bar.minimum() == 0
    assert window.progress_bar.maximum() == 100
    assert window.progress_bar.value() == 3
    assert window.progress_bar.format() == "Preparando..."


def test_gravacao_concluida_aguarda_acao_manual(qtbot, tmp_path: Path):
    compressed = tmp_path / "gravacao.m4a"
    pcm = tmp_path / "captura.wav"
    compressed.write_bytes(b"audio")
    pcm.write_bytes(b"pcm")
    result = RecordingResult(
        final_path=compressed,
        transcription_path=pcm,
        device_name="Microfone USB",
        duration_seconds=2.0,
        recording_format=RECORDING_FORMATS[2],
        peak_dbfs=-6.0,
        warnings=(),
    )
    window = MainWindow()
    qtbot.addWidget(window)
    window._handle_recording_completed(result)

    assert window.worker is None
    assert window.save_audio_button.isEnabled()
    assert window.transcribe_button.isEnabled()
    assert "temporariamente" in window.status_label.text()


def test_salva_audio_do_cache_no_destino_escolhido(qtbot, monkeypatch, tmp_path: Path):
    compressed = tmp_path / "cache.mp3"
    pcm = tmp_path / "captura.wav"
    destination = tmp_path / "reuniao"
    compressed.write_bytes(b"audio-gravado")
    pcm.write_bytes(b"pcm")
    result = RecordingResult(
        final_path=compressed,
        transcription_path=pcm,
        device_name="Microfone",
        duration_seconds=1.0,
        recording_format=RECORDING_FORMATS[0],
        peak_dbfs=-3.0,
        warnings=(),
    )
    window = MainWindow()
    qtbot.addWidget(window)
    window._handle_recording_completed(result)
    monkeypatch.setattr(
        "app.ui.main_window.QFileDialog.getSaveFileName",
        lambda *_args, **_kwargs: (str(destination), "MP3 (*.mp3)"),
    )
    window.save_recording_audio()

    assert (tmp_path / "reuniao.mp3").read_bytes() == b"audio-gravado"
    assert window.selected_audio == (tmp_path / "reuniao.mp3").resolve()


def test_importar_interface_nao_carrega_pytorch_na_abertura():
    command = (
        "import sys; import app.ui.main_window; "
        "raise SystemExit(1 if 'torch' in sys.modules else 0)"
    )
    result = subprocess.run([sys.executable, "-c", command], check=False)
    assert result.returncode == 0


def test_link_de_revisao_posiciona_player(qtbot, monkeypatch):
    window = MainWindow()
    qtbot.addWidget(window)
    positions = []
    monkeypatch.setattr(window.player, "setPosition", positions.append)
    monkeypatch.setattr(window.player, "play", lambda: None)
    from PySide6.QtCore import QUrl

    window._handle_preview_link(QUrl("audio://seek/12.345"))
    assert positions == [12345]
