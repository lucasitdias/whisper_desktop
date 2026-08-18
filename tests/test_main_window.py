from pathlib import Path

from PySide6.QtCore import QThread, Signal

from app.ui.main_window import DropZoneWidget, MainWindow


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

        def __init__(self, _path, parent=None):
            super().__init__(parent)

        @staticmethod
        def device_description():
            return "CPU de teste"

        def run(self):
            self.msleep(80)

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
