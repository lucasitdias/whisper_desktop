"""Janela principal e controles de interação do usuário."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCloseEvent, QDragEnterEvent, QDropEvent, QMouseEvent
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QTabWidget,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.core.exporter import MarkdownExporter
from app.core.transcriber import TranscriberWorker, TranscriptionResult


class DropZoneWidget(QFrame):
    """Área clicável e compatível com arrastar e soltar."""

    file_selected = Signal(str)
    clicked = Signal()
    ALLOWED_SUFFIXES = {".mp3", ".m4a"}

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("dropZone")
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(112)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 18, 24, 18)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        instruction = QLabel("♫  Arraste seu arquivo .mp3 ou .m4a aqui ou clique para selecionar")
        instruction.setAlignment(Qt.AlignmentFlag.AlignCenter)
        instruction.setWordWrap(True)
        self.file_label = QLabel("Nenhum arquivo selecionado")
        self.file_label.setObjectName("mutedLabel")
        self.file_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.file_label.setWordWrap(True)
        layout.addWidget(instruction)
        layout.addWidget(self.file_label)

    @classmethod
    def is_supported(cls, path: str | Path) -> bool:
        return Path(path).suffix.lower() in cls.ALLOWED_SUFFIXES

    def set_file(self, path: Path) -> None:
        self.file_label.setText(path.name)
        self.file_label.setToolTip(str(path))

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        urls = event.mimeData().urls()
        if len(urls) == 1 and urls[0].isLocalFile() and self.is_supported(urls[0].toLocalFile()):
            event.acceptProposedAction()
            self._set_drag_active(True)
        else:
            event.ignore()

    def dragLeaveEvent(self, event) -> None:  # noqa: N802, ANN001
        self._set_drag_active(False)
        super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        self._set_drag_active(False)
        urls = event.mimeData().urls()
        if len(urls) == 1 and urls[0].isLocalFile() and self.is_supported(urls[0].toLocalFile()):
            self.file_selected.emit(urls[0].toLocalFile())
            event.acceptProposedAction()
        else:
            event.ignore()

    def _set_drag_active(self, active: bool) -> None:
        self.setProperty("dragActive", active)
        self.style().unpolish(self)
        self.style().polish(self)


class MainWindow(QMainWindow):
    """Orquestra seleção, worker, visualização, cópia e salvamento."""

    def __init__(self) -> None:
        super().__init__()
        self.selected_audio: Path | None = None
        self.worker: TranscriberWorker | None = None
        self._transcription_failed = False
        self._transcription_cancelled = False
        self.setWindowTitle("Whisper Transcriber Desktop")
        self.resize(1080, 780)
        self.setMinimumSize(820, 640)
        self._build_ui()
        self._update_device_label()

    def _build_ui(self) -> None:
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Whisper Transcriber Desktop")
        title.setObjectName("titleLabel")
        subtitle = QLabel("Transcrição local de MP3 e M4A para Markdown")
        subtitle.setObjectName("mutedLabel")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        self.device_label = QLabel()
        self.device_label.setObjectName("deviceLabel")
        self.device_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        header.addLayout(title_box)
        header.addStretch()
        header.addWidget(self.device_label)
        root.addLayout(header)

        self.drop_zone = DropZoneWidget()
        self.drop_zone.clicked.connect(self.choose_audio)
        self.drop_zone.file_selected.connect(self.set_selected_file)
        root.addWidget(self.drop_zone)

        actions = QHBoxLayout()
        self.transcribe_button = QPushButton("Iniciar Transcrição")
        self.transcribe_button.setObjectName("primaryButton")
        self.transcribe_button.setEnabled(False)
        self.transcribe_button.clicked.connect(self.start_transcription)
        self.cancel_button = QPushButton("Cancelar Transcrição")
        self.cancel_button.setObjectName("dangerButton")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_transcription)
        self.copy_button = QPushButton("Copiar Markdown")
        self.copy_button.setObjectName("secondaryButton")
        self.copy_button.setEnabled(False)
        self.copy_button.clicked.connect(self.copy_markdown)
        self.save_button = QPushButton("Salvar como...")
        self.save_button.setObjectName("secondaryButton")
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self.save_markdown)
        actions.addWidget(self.transcribe_button)
        actions.addWidget(self.cancel_button)
        actions.addStretch()
        actions.addWidget(self.copy_button)
        actions.addWidget(self.save_button)
        root.addLayout(actions)

        self.status_label = QLabel("Selecione um arquivo para começar.")
        self.status_label.setObjectName("statusLabel")
        root.addWidget(self.status_label)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        root.addWidget(self.progress_bar)
        self.coverage_label = QLabel(
            "Após concluir, a cobertura do áudio e a confiança estimada aparecerão aqui."
        )
        self.coverage_label.setObjectName("mutedLabel")
        self.coverage_label.setWordWrap(True)
        root.addWidget(self.coverage_label)

        self.log_viewer = QPlainTextEdit()
        self.log_viewer.setObjectName("logViewer")
        self.log_viewer.setReadOnly(True)
        self.log_viewer.setMaximumHeight(105)
        self.log_viewer.setPlaceholderText("As etapas da transcrição aparecerão aqui.")
        root.addWidget(self.log_viewer)

        section = QLabel("Resultado")
        section.setObjectName("sectionLabel")
        root.addWidget(section)
        self.tabs = QTabWidget()
        self.source_editor = QTextEdit()
        self.source_editor.setPlaceholderText("O Markdown gerado aparecerá aqui.")
        self.source_editor.textChanged.connect(self.update_preview)
        self.preview = QTextBrowser()
        self.preview.setOpenExternalLinks(False)
        self.tabs.addTab(self.source_editor, "Markdown")
        self.tabs.addTab(self.preview, "Visualização")
        root.addWidget(self.tabs, stretch=1)
        self.setCentralWidget(central)

    def _update_device_label(self) -> None:
        self.device_label.setText(TranscriberWorker.device_description())

    def choose_audio(self) -> None:
        if self.worker is not None:
            return
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar arquivo de áudio",
            "",
            "Áudio compatível (*.mp3 *.m4a)",
        )
        if path:
            self.set_selected_file(path)

    def set_selected_file(self, path: str) -> bool:
        if self.worker is not None:
            return False
        candidate = Path(path)
        if not candidate.is_file() or not DropZoneWidget.is_supported(candidate):
            QMessageBox.warning(self, "Arquivo inválido", "Selecione um arquivo MP3 ou M4A válido.")
            return False
        self.selected_audio = candidate.resolve()
        self.drop_zone.set_file(self.selected_audio)
        self.status_label.setText("Arquivo pronto para transcrição.")
        self.coverage_label.setText(
            "Após concluir, a cobertura do áudio e a confiança estimada aparecerão aqui."
        )
        self.transcribe_button.setEnabled(True)
        return True

    def start_transcription(self) -> None:
        if self.selected_audio is None or self.worker is not None:
            return
        self.source_editor.clear()
        self.preview.clear()
        self.log_viewer.clear()
        self.copy_button.setEnabled(False)
        self.save_button.setEnabled(False)
        self.transcribe_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.drop_zone.setEnabled(False)
        self._transcription_failed = False
        self._transcription_cancelled = False
        self.coverage_label.setText("Cobertura em análise durante a transcrição...")
        self.worker = TranscriberWorker(self.selected_audio, self)
        self.worker.status_changed.connect(self._handle_status)
        self.worker.progress_changed.connect(self._handle_progress)
        self.worker.segment_decoded.connect(self._handle_segment)
        self.worker.completed.connect(self._handle_result)
        self.worker.failed.connect(self._handle_failure)
        self.worker.cancelled.connect(self._handle_cancelled)
        self.worker.finished.connect(self._thread_finished)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.start()

    def cancel_transcription(self) -> None:
        if self.worker is None or not self.worker.isRunning():
            return
        self.cancel_button.setEnabled(False)
        self.status_label.setText(
            "Cancelamento solicitado; finalizando a etapa atual com segurança..."
        )
        self.log_viewer.appendPlainText(self.status_label.text())
        self.worker.cancel()

    def _handle_status(self, message: str) -> None:
        self.status_label.setText(message)
        self.log_viewer.appendPlainText(message)

    def _handle_progress(self, value: int) -> None:
        if value < 0:
            self.progress_bar.setRange(0, 0)
        else:
            if self.progress_bar.maximum() == 0:
                self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(value)

    def _handle_segment(self, text: str) -> None:
        self.log_viewer.appendPlainText(f"Trecho: {text}")

    def _handle_result(self, result: TranscriptionResult) -> None:
        markdown = MarkdownExporter.render(result)
        self.source_editor.setPlainText(markdown)
        self.copy_button.setEnabled(True)
        self.save_button.setEnabled(True)
        self.tabs.setCurrentIndex(0)
        duration = MarkdownExporter.format_timestamp(result.duration_seconds)
        confidence = (
            f" Confiança média estimada: {result.average_word_confidence * 100:.1f}% "
            f"em {result.word_count} palavras; {result.low_confidence_word_count} abaixo de 50%."
            if result.average_word_confidence is not None
            else " Confiança por palavra indisponível para este resultado."
        )
        self.coverage_label.setText(
            f"Cobertura: {result.processing_coverage_percent:.0f}% do áudio processado "
            f"({duration}).{confidence}"
        )
        self.log_viewer.appendPlainText(self.coverage_label.text())

    def _handle_failure(self, message: str) -> None:
        self._transcription_failed = True
        self._handle_progress(0)
        self.status_label.setText(message)
        self.log_viewer.appendPlainText(message)
        QMessageBox.critical(self, "Falha na transcrição", message)

    def _handle_cancelled(self, message: str) -> None:
        self._transcription_cancelled = True
        self._handle_progress(0)
        self.status_label.setText(message)
        self.coverage_label.setText("Transcrição interrompida: a cobertura não foi concluída.")

    def _thread_finished(self) -> None:
        self.worker = None
        self.cancel_button.setEnabled(False)
        self.drop_zone.setEnabled(True)
        self.transcribe_button.setEnabled(self.selected_audio is not None)
        if (
            not self._transcription_failed
            and not self._transcription_cancelled
            and self.source_editor.toPlainText()
        ):
            self._handle_progress(100)

    def update_preview(self) -> None:
        self.preview.setMarkdown(self.source_editor.toPlainText())

    def copy_markdown(self) -> None:
        markdown = self.source_editor.toPlainText()
        if not markdown:
            return
        QApplication.clipboard().setText(markdown)
        self.status_label.setText("Markdown copiado para a área de transferência.")

    def save_markdown(self) -> None:
        if not self.source_editor.toPlainText() or self.selected_audio is None:
            return
        suggestion = self.selected_audio.with_name(f"{self.selected_audio.stem}_transcricao.md")
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Salvar transcrição em Markdown",
            str(suggestion),
            "Markdown (*.md)",
        )
        if not path:
            return
        target = Path(path)
        if target.suffix.lower() != ".md":
            target = target.with_suffix(".md")
        if target.exists():
            answer = QMessageBox.question(
                self,
                "Confirmar substituição",
                f"O arquivo {target.name} já existe. Deseja substituí-lo?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        try:
            saved = MarkdownExporter.save(self.source_editor.toPlainText(), target)
        except OSError as error:
            QMessageBox.critical(self, "Falha ao salvar", f"Não foi possível salvar: {error}")
            return
        self.status_label.setText(f"Transcrição salva em {saved.name}.")

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        if self.worker is not None and self.worker.isRunning():
            QMessageBox.information(
                self,
                "Transcrição em andamento",
                "Cancele a transcrição e aguarde a confirmação antes de fechar o aplicativo.",
            )
            event.ignore()
            return
        event.accept()
