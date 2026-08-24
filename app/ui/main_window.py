"""Janela principal, gravação, transcrição e revisão assistida."""

from __future__ import annotations

import shutil
import time
from pathlib import Path
from typing import Any

from PySide6.QtCore import QMicrophonePermission, QProcess, QSize, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import (
    QCloseEvent,
    QDragEnterEvent,
    QDropEvent,
    QKeySequence,
    QMouseEvent,
    QShortcut,
)
from PySide6.QtMultimedia import QAudioOutput, QMediaDevices, QMediaPlayer
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSplitter,
    QStyle,
    QTabWidget,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.core.exporter import MarkdownExporter
from app.core.model_catalog import (
    MODEL_BY_ID,
    MODEL_SPECS,
    ModelAvailability,
    ModelDownloadWorker,
    ModelManager,
    ModelSpec,
)
from app.core.recorder import (
    RECORDING_FORMATS,
    RecorderController,
    RecordingFormat,
    RecordingResult,
    RecordingState,
)
from app.core.telemetry import ProcessResourceSampler
from app.core.transcriber import (
    TranscriberWorker,
    TranscriptionOptions,
    TranscriptionPriority,
    TranscriptionResult,
)


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
        self.setMinimumHeight(88)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 14, 24, 14)
        layout.setSpacing(5)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        instruction = QLabel("Arraste um arquivo MP3/M4A aqui ou clique para selecionar")
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

    def dragLeaveEvent(self, event: Any) -> None:  # noqa: N802
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
    """Orquestra captura, transcrição, exportação e revisão do áudio."""

    def __init__(self) -> None:
        super().__init__()
        self.selected_audio: Path | None = None
        self.worker: TranscriberWorker | None = None
        self.model_download_worker: ModelDownloadWorker | None = None
        self._selected_model_id: str | None = None
        self._result_focus = False
        self._normal_splitter_sizes = [600, 300]
        self._transcription_failed = False
        self._transcription_cancelled = False
        self._transcription_temporary: Path | None = None
        self._recording_result: RecordingResult | None = None
        self._recording_saved = False
        self._pending_recording: tuple[Any, RecordingFormat] | None = None
        self._transcription_started_at: float | None = None
        self._transcription_elapsed_seconds = 0.0
        self._active_processing_device: str | None = None
        self._gpu_utilization: int | None = None
        self._gpu_memory_used_mb: int | None = None
        self._gpu_memory_total_mb: int | None = None
        self._nvidia_smi = shutil.which("nvidia-smi")
        self.recorder = RecorderController(self)
        self.media_devices = QMediaDevices(self)
        self.player = QMediaPlayer(self)
        self.player_output = QAudioOutput(self)
        self.player.setAudioOutput(self.player_output)
        self.setWindowTitle("Whisper Transcriber Desktop")
        self.resize(1240, 860)
        self.setMinimumSize(820, 640)
        self._build_ui()
        self._connect_services()
        self._resource_sampler = ProcessResourceSampler()
        self._gpu_probe = QProcess(self)
        self._gpu_probe.readyReadStandardOutput.connect(self._read_gpu_probe)
        self._telemetry_timer = QTimer(self)
        self._telemetry_timer.setInterval(1000)
        self._telemetry_timer.timeout.connect(self._update_telemetry)
        self._telemetry_timer.start()
        self._model_release_timer = QTimer(self)
        self._model_release_timer.setSingleShot(True)
        self._model_release_timer.setInterval(
            getattr(TranscriberWorker, "MODEL_CACHE_IDLE_MS", 5 * 60 * 1000)
        )
        self._model_release_timer.timeout.connect(self._release_idle_model)
        self._update_telemetry()
        self._refresh_audio_inputs()
        self._update_device_label()
        self._device_refresh_timer = QTimer(self)
        self._device_refresh_timer.setInterval(2000)
        self._device_refresh_timer.timeout.connect(self._refresh_audio_inputs)
        self._device_refresh_timer.start()

    def _build_ui(self) -> None:
        central = QWidget()
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setObjectName("mainScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        host = QWidget()
        host_layout = QHBoxLayout(host)
        host_layout.setContentsMargins(20, 18, 20, 24)
        host_layout.addStretch()
        page = QWidget()
        page.setObjectName("contentPage")
        page.setMaximumWidth(1480)
        page.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        root = QVBoxLayout(page)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(16)
        host_layout.addWidget(page, 1)
        host_layout.addStretch()
        scroll.setWidget(host)
        self.top_scroll = scroll

        header = QVBoxLayout()
        header.setSpacing(6)
        title_box = QVBoxLayout()
        title_box.setSpacing(3)
        title = QLabel("Whisper Transcriber Desktop")
        title.setObjectName("titleLabel")
        subtitle = QLabel("Gravação e transcrição local com privacidade e alta precisão")
        subtitle.setObjectName("mutedLabel")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        self.device_label = QLabel()
        self.device_label.setObjectName("deviceLabel")
        self.device_label.setWordWrap(True)
        self.device_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        header.addLayout(title_box)
        header.addWidget(self.device_label)
        root.addLayout(header)

        recording_card = QFrame()
        recording_card.setObjectName("cardPanel")
        recording = QGridLayout(recording_card)
        recording.setContentsMargins(20, 18, 20, 18)
        recording.setHorizontalSpacing(16)
        recording.setVerticalSpacing(10)
        recording.addWidget(self._section_label("Gravação de áudio"), 0, 0, 1, 2)
        recording_help = QLabel(
            "Escolha a entrada e o formato. O áudio ficará em cache até você salvar "
            "ou iniciar a transcrição."
        )
        recording_help.setObjectName("mutedLabel")
        recording_help.setWordWrap(True)
        recording.addWidget(recording_help, 1, 0, 1, 2)

        recording.addWidget(QLabel("Microfone"), 2, 0)
        recording.addWidget(QLabel("Formato do arquivo"), 2, 1)
        microphone_row = QHBoxLayout()
        microphone_row.setSpacing(8)
        self.microphone_combo = QComboBox()
        self.microphone_combo.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed
        )
        self.microphone_combo.setMinimumContentsLength(18)
        self.microphone_combo.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.refresh_microphones_button = QPushButton("Atualizar")
        self.refresh_microphones_button.setObjectName("compactButton")
        self.refresh_microphones_button.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload)
        )
        self.refresh_microphones_button.setToolTip(
            "Procura novamente microfones internos, USB, headset e Bluetooth."
        )
        microphone_row.addWidget(self.microphone_combo, 1)
        microphone_row.addWidget(self.refresh_microphones_button)
        recording.addLayout(microphone_row, 3, 0)
        self.recording_format_combo = QComboBox()
        self.recording_format_combo.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed
        )
        for recording_format in RECORDING_FORMATS:
            self.recording_format_combo.addItem(recording_format.label, recording_format)
        self.recording_format_combo.setMaximumWidth(320)
        recording.addWidget(self.recording_format_combo, 3, 1)
        recording.setColumnStretch(0, 3)
        recording.setColumnStretch(1, 1)

        controls = QHBoxLayout()
        controls.setSpacing(8)
        self.record_button = QPushButton("Gravar")
        self.record_button.setObjectName("recordButton")
        # O Qt não fornece SP_MediaRecord em todas as versões suportadas.
        # Mantemos o texto nativo no botão de gravação para evitar glifos
        # dependentes de fonte e preservar a abertura da interface.
        self.pause_recording_button = QPushButton("Pausar")
        self.pause_recording_button.setObjectName("secondaryButton")
        self.pause_recording_button.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause)
        )
        self.pause_recording_button.setEnabled(False)
        self.stop_recording_button = QPushButton("Parar")
        self.stop_recording_button.setObjectName("dangerButton")
        self.stop_recording_button.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_MediaStop)
        )
        self.stop_recording_button.setEnabled(False)
        self.save_audio_button = QPushButton("Salvar áudio como...")
        self.save_audio_button.setObjectName("secondaryButton")
        self.save_audio_button.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton)
        )
        self.save_audio_button.setEnabled(False)
        for button in (
            self.record_button,
            self.pause_recording_button,
            self.stop_recording_button,
            self.save_audio_button,
            self.refresh_microphones_button,
        ):
            button.setIconSize(QSize(16, 16))
        self.recording_timer = QLabel("00:00:00")
        self.recording_timer.setObjectName("timerLabel")
        controls.addWidget(self.record_button)
        controls.addWidget(self.pause_recording_button)
        controls.addWidget(self.stop_recording_button)
        controls.addSpacing(8)
        controls.addWidget(self.recording_timer)
        controls.addStretch(1)
        recording.addLayout(controls, 4, 0, 1, 2)

        level_row = QHBoxLayout()
        level_row.setSpacing(10)
        level_row.addWidget(self.save_audio_button)
        level_row.addSpacing(8)
        level_label = QLabel("Nível de entrada")
        level_label.setObjectName("mutedLabel")
        level_row.addWidget(level_label)
        self.level_meter = QProgressBar()
        self.level_meter.setRange(0, 100)
        self.level_meter.setValue(0)
        self.level_meter.setTextVisible(False)
        self.level_meter.setMinimumWidth(160)
        self.level_meter.setMaximumWidth(320)
        level_row.addWidget(self.level_meter, 1)
        level_row.addStretch(2)
        recording.addLayout(level_row, 5, 0, 1, 2)
        self.recording_status = QLabel("Microfones reconhecidos automaticamente pelo sistema.")
        self.recording_status.setObjectName("mutedLabel")
        self.recording_status.setWordWrap(True)
        recording.addWidget(self.recording_status, 6, 0, 1, 2)
        root.addWidget(recording_card)

        self.drop_zone = DropZoneWidget()
        root.addWidget(self.drop_zone)

        settings_card = QFrame()
        settings_card.setObjectName("cardPanel")
        settings = QGridLayout(settings_card)
        settings.setContentsMargins(20, 18, 20, 18)
        settings.setHorizontalSpacing(16)
        settings.setVerticalSpacing(9)
        settings.addWidget(self._section_label("Configurações da transcrição"), 0, 0, 1, 2)
        settings.addWidget(QLabel("Modelo de transcrição"), 1, 0)
        settings.addWidget(QLabel("Contexto opcional"), 1, 1)
        self.model_combo = QComboBox()
        self.model_combo.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        for spec in MODEL_SPECS:
            self.model_combo.addItem(spec.display_label, spec.model_id)
            self.model_combo.setItemData(
                self.model_combo.count() - 1, spec.tooltip, Qt.ItemDataRole.ToolTipRole
            )
        self.model_combo.setCurrentIndex(self.model_combo.findData("large-v3"))
        self.model_combo.setMaximumWidth(520)
        settings.addWidget(self.model_combo, 2, 0)
        self.context_input = QLineEdit()
        self.context_input.setMaxLength(1000)
        self.context_input.setPlaceholderText("Ex.: nomes próprios, siglas e termos técnicos")
        settings.addWidget(self.context_input, 2, 1)
        settings.setColumnStretch(0, 1)
        settings.setColumnStretch(1, 3)
        self.model_status_label = QLabel()
        self.model_status_label.setObjectName("modelStatusLabel")
        self.model_status_label.setWordWrap(True)
        settings.addWidget(self.model_status_label, 3, 0, 1, 2)
        model_actions = QHBoxLayout()
        model_actions.setSpacing(8)
        self.model_download_button = QPushButton("Baixar modelo")
        self.model_download_button.setObjectName("secondaryButton")
        self.model_download_button.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowDown)
        )
        self.model_download_cancel_button = QPushButton("Cancelar download")
        self.model_download_cancel_button.setObjectName("dangerButton")
        self.model_download_cancel_button.setEnabled(False)
        model_actions.addWidget(self.model_download_button)
        model_actions.addWidget(self.model_download_cancel_button)
        model_actions.addStretch(1)
        settings.addLayout(model_actions, 4, 0, 1, 2)
        self.selective_review_checkbox = QCheckBox("Revisar automaticamente trechos duvidosos")
        self.selective_review_checkbox.setToolTip(
            "Executa uma segunda passagem apenas em trechos de baixa confiança; "
            "pode aumentar o tempo."
        )
        settings.addWidget(QLabel("Prioridade da transcrição"), 5, 0)
        self.priority_combo = QComboBox()
        self.priority_combo.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed
        )
        self.priority_combo.setMaximumWidth(520)
        priority_items = (
            (
                "Velocidade — resposta mais rápida",
                TranscriptionPriority.FAST,
                "Reduz a busca para priorizar tempo; indicado para rascunhos e hardware modesto.",
            ),
            (
                "Equilibrada — qualidade e desempenho",
                TranscriptionPriority.BALANCED,
                "Usa a busca recomendada para cada modelo e mantém o melhor equilíbrio geral.",
            ),
            (
                "Maior fidelidade — análise reforçada",
                TranscriptionPriority.MAX_FIDELITY,
                "Usa busca ampliada, maior paciência e revisão automática dos trechos duvidosos.",
            ),
        )
        for label, priority, tooltip in priority_items:
            self.priority_combo.addItem(label, priority.value)
            self.priority_combo.setItemData(
                self.priority_combo.count() - 1,
                tooltip,
                Qt.ItemDataRole.ToolTipRole,
            )
        self.priority_combo.setCurrentIndex(
            self.priority_combo.findData(TranscriptionPriority.BALANCED.value)
        )
        settings.addWidget(self.priority_combo, 6, 0)
        settings.addWidget(self.selective_review_checkbox, 7, 0, 1, 2)
        root.addWidget(settings_card)

        actions = QVBoxLayout()
        actions.setSpacing(8)
        transcription_actions = QHBoxLayout()
        transcription_actions.setSpacing(8)
        export_actions = QHBoxLayout()
        export_actions.setSpacing(8)
        self.transcribe_button = QPushButton("Iniciar transcrição")
        self.transcribe_button.setObjectName("primaryButton")
        self.transcribe_button.setEnabled(False)
        self.cancel_button = QPushButton("Cancelar")
        self.cancel_button.setObjectName("dangerButton")
        self.cancel_button.setEnabled(False)
        self.copy_button = QPushButton("Copiar Markdown")
        self.copy_button.setObjectName("secondaryButton")
        self.copy_button.setEnabled(False)
        self.save_button = QPushButton("Salvar transcrição...")
        self.save_button.setObjectName("secondaryButton")
        self.save_button.setEnabled(False)
        transcription_actions.addWidget(self.transcribe_button)
        transcription_actions.addWidget(self.cancel_button)
        transcription_actions.addStretch(1)
        export_actions.addStretch(1)
        export_actions.addWidget(self.copy_button)
        export_actions.addWidget(self.save_button)
        actions.addLayout(transcription_actions)
        actions.addLayout(export_actions)
        root.addLayout(actions)

        self.status_label = QLabel("Selecione um arquivo ou grave um novo áudio.")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setWordWrap(True)
        root.addWidget(self.status_label)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        root.addWidget(self.progress_bar)
        telemetry_card = QFrame()
        telemetry_card.setObjectName("telemetryPanel")
        telemetry_layout = QHBoxLayout(telemetry_card)
        telemetry_layout.setContentsMargins(14, 10, 14, 10)
        telemetry_layout.setSpacing(12)
        telemetry_title = QLabel("Monitor de processamento")
        telemetry_title.setObjectName("telemetryTitle")
        self.telemetry_label = QLabel(
            "Tempo: 00:00:00  •  CPU do app: 0%  •  RAM do app: medindo...  •  "
            "GPU: aguardando transcrição  •  VRAM: —"
        )
        self.telemetry_label.setObjectName("telemetryLabel")
        self.telemetry_label.setWordWrap(True)
        self.telemetry_label.setToolTip(
            "CPU e RAM são do aplicativo. Em NVIDIA, GPU e VRAM vêm do driver e "
            "representam o uso total da placa durante a transcrição."
        )
        telemetry_layout.addWidget(telemetry_title)
        telemetry_layout.addWidget(self.telemetry_label, 1)
        root.addWidget(telemetry_card)
        self.coverage_label = QLabel(
            "Após concluir, cobertura, confiança e pontos de revisão aparecerão aqui."
        )
        self.coverage_label.setObjectName("mutedLabel")
        self.coverage_label.setWordWrap(True)
        root.addWidget(self.coverage_label)

        player_card = QFrame()
        player_card.setObjectName("cardPanel")
        player_row = QHBoxLayout(player_card)
        player_row.setContentsMargins(16, 12, 16, 12)
        player_row.setSpacing(10)
        player_row.addWidget(QLabel("Revisão do áudio"))
        self.player_button = QPushButton("Reproduzir")
        self.player_button.setObjectName("compactButton")
        self.player_button.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay)
        )
        self.player_button.setIconSize(QSize(16, 16))
        self.player_button.setMinimumWidth(126)
        self.player_button.setEnabled(False)
        self.player_slider = QSlider(Qt.Orientation.Horizontal)
        self.player_slider.setRange(0, 0)
        self.player_slider.setEnabled(False)
        self.player_time = QLabel("00:00 / 00:00")
        self.player_time.setObjectName("mutedLabel")
        self.player_time.setMinimumWidth(92)
        self.player_time.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        player_row.addWidget(self.player_button)
        player_row.addWidget(self.player_slider, 1)
        player_row.addWidget(self.player_time)
        root.addWidget(player_card)

        self.log_viewer = QPlainTextEdit()
        self.log_viewer.setObjectName("logViewer")
        self.log_viewer.setReadOnly(True)
        self.log_viewer.setMaximumHeight(116)
        self.log_viewer.setPlaceholderText("As etapas de processamento aparecerão aqui.")
        root.addWidget(self.log_viewer)
        root.addStretch(1)

        self.result_panel = QFrame()
        self.result_panel.setObjectName("resultPanel")
        result_layout = QVBoxLayout(self.result_panel)
        result_layout.setContentsMargins(20, 12, 20, 18)
        result_layout.setSpacing(8)
        result_toolbar = QHBoxLayout()
        result_toolbar.setSpacing(8)
        result_toolbar.addWidget(self._section_label("Resultado"))
        result_toolbar.addStretch(1)
        self.expand_result_button = QPushButton("Expandir resultado")
        self.expand_result_button.setObjectName("compactButton")
        self.expand_result_button.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarMaxButton)
        )
        self.expand_result_button.setToolTip(
            "Oculta temporariamente os controles e amplia Markdown/Visualização."
        )
        result_toolbar.addWidget(self.expand_result_button)
        result_layout.addLayout(result_toolbar)
        self.tabs = QTabWidget()
        self.tabs.setMinimumHeight(210)
        self.source_editor = QTextEdit()
        self.source_editor.setPlaceholderText("O Markdown gerado aparecerá aqui.")
        self.preview = QTextBrowser()
        self.preview.setOpenExternalLinks(False)
        self.preview.setOpenLinks(False)
        self.tabs.addTab(self.source_editor, "Markdown")
        self.tabs.addTab(self.preview, "Visualização")
        result_layout.addWidget(self.tabs, 1)

        self.main_splitter = QSplitter(Qt.Orientation.Vertical)
        self.main_splitter.setObjectName("mainSplitter")
        self.main_splitter.setChildrenCollapsible(False)
        self.main_splitter.addWidget(self.top_scroll)
        self.main_splitter.addWidget(self.result_panel)
        self.main_splitter.setStretchFactor(0, 2)
        self.main_splitter.setStretchFactor(1, 1)
        self.main_splitter.setSizes(self._normal_splitter_sizes)
        outer.addWidget(self.main_splitter)
        self.setCentralWidget(central)

        self._escape_focus_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        self._escape_focus_shortcut.setEnabled(False)

    @staticmethod
    def _section_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("sectionLabel")
        return label

    def _connect_services(self) -> None:
        self.drop_zone.clicked.connect(self.choose_audio)
        self.drop_zone.file_selected.connect(self.set_selected_file)
        self.transcribe_button.clicked.connect(self.start_transcription)
        self.cancel_button.clicked.connect(self.cancel_transcription)
        self.copy_button.clicked.connect(self.copy_markdown)
        self.save_button.clicked.connect(self.save_markdown)
        self.save_audio_button.clicked.connect(self.save_recording_audio)
        self.source_editor.textChanged.connect(self.update_preview)
        self.record_button.clicked.connect(self.start_recording)
        self.pause_recording_button.clicked.connect(self.toggle_recording_pause)
        self.stop_recording_button.clicked.connect(self.recorder.stop)
        self.recorder.state_changed.connect(self._handle_recording_state)
        self.recorder.elapsed_changed.connect(self._handle_recording_elapsed)
        self.recorder.level_changed.connect(self._handle_recording_level)
        self.recorder.completed.connect(self._handle_recording_completed)
        self.recorder.failed.connect(self._handle_recording_failure)
        self.media_devices.audioInputsChanged.connect(self._refresh_audio_inputs)
        self.refresh_microphones_button.clicked.connect(self._refresh_audio_inputs)
        self.model_combo.currentIndexChanged.connect(self._update_model_state)
        self.priority_combo.currentIndexChanged.connect(self._update_priority_state)
        self.model_download_button.clicked.connect(self.download_selected_model)
        self.model_download_cancel_button.clicked.connect(self.cancel_model_download)
        self.expand_result_button.clicked.connect(self.toggle_result_focus)
        self._escape_focus_shortcut.activated.connect(self.restore_result_focus)
        self.player_button.clicked.connect(self.toggle_playback)
        self.player_slider.sliderMoved.connect(self.player.setPosition)
        self.player.positionChanged.connect(self._update_player_position)
        self.player.durationChanged.connect(self._update_player_duration)
        self.player.playbackStateChanged.connect(self._update_player_button)
        self.preview.anchorClicked.connect(self._handle_preview_link)
        self._update_model_state()
        self._update_priority_state()

    def _update_device_label(self) -> None:
        self.device_label.setText(
            "Processamento: GPU/CPU será confirmado ao iniciar a transcrição"
        )

    def _selected_model_spec(self) -> ModelSpec:
        model_id = str(self.model_combo.currentData())
        return MODEL_BY_ID.get(model_id, MODEL_BY_ID["large-v3"])

    def _update_model_state(self, *_args: Any) -> None:
        spec = self._selected_model_spec()
        if self._selected_model_id and self._selected_model_id != spec.model_id:
            self._model_release_timer.stop()
            self._release_transcriber_model()
        self._selected_model_id = spec.model_id
        self.model_combo.setToolTip(spec.tooltip)
        availability = ModelManager.availability(spec)
        messages = {
            ModelAvailability.BUNDLED: (
                f"Disponível offline — incluído no aplicativo. {spec.tooltip}"
            ),
            ModelAvailability.CACHED: (
                f"Disponível offline — armazenado neste computador. {spec.tooltip}"
            ),
            ModelAvailability.DOWNLOAD_REQUIRED: (
                f"Requer download explícito de {spec.size_label}; depois funcionará offline."
            ),
            ModelAvailability.INVALID: (
                "O arquivo local está incompleto ou inválido. Baixe novamente para reparar."
            ),
            ModelAvailability.DOWNLOADING: "Download em andamento...",
        }
        self.model_status_label.setText(messages[availability])
        ready = availability in {ModelAvailability.BUNDLED, ModelAvailability.CACHED}
        downloading = self.model_download_worker is not None
        self.model_download_button.setText(
            "Reparar modelo" if availability is ModelAvailability.INVALID else "Baixar modelo"
        )
        self.model_download_button.setEnabled(
            not ready and not downloading and self.worker is None
        )
        self.model_download_cancel_button.setEnabled(downloading)
        self._refresh_transcribe_enabled()

    def _model_ready(self) -> bool:
        return ModelManager.availability(self._selected_model_spec()) in {
            ModelAvailability.BUNDLED,
            ModelAvailability.CACHED,
        }

    def _refresh_transcribe_enabled(self) -> None:
        self.transcribe_button.setEnabled(
            self.selected_audio is not None
            and self.worker is None
            and self.model_download_worker is None
            and self.recorder.state is RecordingState.READY
            and self._model_ready()
        )

    def download_selected_model(self) -> None:
        if self.worker is not None or self.model_download_worker is not None:
            return
        spec = self._selected_model_spec()
        if self._model_ready():
            self._update_model_state()
            return
        self.model_download_worker = ModelDownloadWorker(spec, self)
        self.model_download_worker.progress_changed.connect(self._handle_progress)
        self.model_download_worker.status_changed.connect(self._handle_status)
        self.model_download_worker.completed.connect(self._handle_model_downloaded)
        self.model_download_worker.failed.connect(self._handle_model_download_failure)
        self.model_download_worker.cancelled.connect(self._handle_model_download_cancelled)
        self.model_download_worker.finished.connect(self._model_download_finished)
        self.model_download_worker.finished.connect(
            self.model_download_worker.deleteLater
        )
        self.model_combo.setEnabled(False)
        self.model_download_button.setEnabled(False)
        self.model_download_cancel_button.setEnabled(True)
        self._refresh_transcribe_enabled()
        self.model_download_worker.start()

    def cancel_model_download(self) -> None:
        if self.model_download_worker is None:
            return
        self.model_download_cancel_button.setEnabled(False)
        self.model_download_worker.cancel()

    def _handle_model_downloaded(self, path: object) -> None:
        checkpoint = Path(path)
        self.status_label.setText(
            f"Modelo {self._selected_model_spec().model_id} disponível offline "
            f"({checkpoint.stat().st_size / (1024**2):.0f} MB)."
        )
        self._handle_progress(100)

    def _handle_model_download_failure(self, message: str) -> None:
        self._handle_progress(0)
        self.status_label.setText(message)
        QMessageBox.warning(self, "Falha ao baixar modelo", message)

    def _handle_model_download_cancelled(self, message: str) -> None:
        self._handle_progress(0)
        self.status_label.setText(message)

    def _model_download_finished(self) -> None:
        self.model_download_worker = None
        self.model_combo.setEnabled(self.worker is None)
        self.model_download_cancel_button.setEnabled(False)
        self._update_model_state()

    def toggle_result_focus(self) -> None:
        if self._result_focus:
            self.restore_result_focus()
            return
        sizes = self.main_splitter.sizes()
        if sizes and sizes[0] > 0:
            self._normal_splitter_sizes = sizes
        self._result_focus = True
        self.top_scroll.hide()
        self.expand_result_button.setText("Restaurar")
        self.expand_result_button.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarNormalButton)
        )
        self.expand_result_button.setToolTip("Restaura os controles da aplicação (Esc).")
        self._escape_focus_shortcut.setEnabled(True)
        self.source_editor.setFocus() if self.tabs.currentIndex() == 0 else self.preview.setFocus()

    def restore_result_focus(self) -> None:
        if not self._result_focus:
            return
        self._result_focus = False
        self.top_scroll.show()
        self.main_splitter.setSizes(self._normal_splitter_sizes)
        self.expand_result_button.setText("Expandir resultado")
        self.expand_result_button.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarMaxButton)
        )
        self.expand_result_button.setToolTip(
            "Oculta temporariamente os controles e amplia Markdown/Visualização."
        )
        self._escape_focus_shortcut.setEnabled(False)

    def _refresh_audio_inputs(self) -> None:
        selected_id = None
        selected = self.microphone_combo.currentData()
        if selected is not None and not selected.isNull():
            selected_id = bytes(selected.id())
        devices = QMediaDevices.audioInputs()
        if self.recorder.state is not RecordingState.READY:
            return
        current_ids = [
            bytes(self.microphone_combo.itemData(index).id())
            for index in range(self.microphone_combo.count())
            if self.microphone_combo.itemData(index) is not None
            and not self.microphone_combo.itemData(index).isNull()
        ]
        device_ids = [bytes(device.id()) for device in devices]
        if current_ids == device_ids:
            self.record_button.setEnabled(bool(devices) and not self._is_busy())
            return
        self.microphone_combo.blockSignals(True)
        self.microphone_combo.clear()
        selected_index = -1
        default_device = QMediaDevices.defaultAudioInput()
        default_id = bytes(default_device.id()) if not default_device.isNull() else None
        for index, device in enumerate(devices):
            self.microphone_combo.addItem(device.description(), device)
            selected_matches = selected_id is not None and bytes(device.id()) == selected_id
            default_matches = (
                selected_id is None
                and default_id is not None
                and bytes(device.id()) == default_id
            )
            if selected_matches or default_matches:
                selected_index = index
        if selected_index >= 0:
            self.microphone_combo.setCurrentIndex(selected_index)
        self.microphone_combo.blockSignals(False)
        self.record_button.setEnabled(bool(devices) and not self._is_busy())
        if not devices:
            self.recording_status.setText("Nenhum microfone foi reconhecido pelo sistema.")
        else:
            self.recording_status.setText(
                f"{len(devices)} entrada(s) de áudio reconhecida(s) automaticamente."
            )

    def _is_busy(self) -> bool:
        return self.worker is not None or self.recorder.state is not RecordingState.READY

    def choose_audio(self) -> None:
        if self._is_busy():
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Selecionar arquivo de áudio", "", "Áudio compatível (*.mp3 *.m4a)"
        )
        if path:
            self.set_selected_file(path)

    def set_selected_file(self, path: str) -> bool:
        if self._is_busy():
            return False
        candidate = Path(path)
        if not candidate.is_file() or not DropZoneWidget.is_supported(candidate):
            QMessageBox.warning(self, "Arquivo inválido", "Selecione um arquivo MP3 ou M4A válido.")
            return False
        self._discard_cached_recording()
        self.selected_audio = candidate.resolve()
        self.drop_zone.set_file(self.selected_audio)
        self.status_label.setText("Arquivo pronto para transcrição.")
        self.coverage_label.setText(
            "Após concluir, cobertura, confiança e pontos de revisão aparecerão aqui."
        )
        self._refresh_transcribe_enabled()
        self.save_audio_button.setEnabled(False)
        self._set_player_source(self.selected_audio)
        return True

    def start_recording(self) -> None:
        if self._is_busy():
            return
        device = self.microphone_combo.currentData()
        recording_format = self.recording_format_combo.currentData()
        if device is None or device.isNull() or not isinstance(recording_format, RecordingFormat):
            QMessageBox.warning(self, "Microfone indisponível", "Selecione um microfone válido.")
            return
        if self._recording_result is not None and not self._recording_saved:
            answer = QMessageBox.question(
                self,
                "Descartar gravação em cache?",
                "Existe uma gravação ainda não salva. Deseja descartá-la e iniciar outra?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer is not QMessageBox.StandardButton.Yes:
                return
        self._discard_cached_recording()
        self._pending_recording = (device, recording_format)
        permission = QMicrophonePermission()
        app = QApplication.instance()
        status = app.checkPermission(permission)
        if status is Qt.PermissionStatus.Undetermined:
            app.requestPermission(permission, self, self._after_microphone_permission)
            return
        self._after_microphone_permission()

    def _after_microphone_permission(self, *_args: Any) -> None:
        if self._pending_recording is None:
            return
        app = QApplication.instance()
        if app.checkPermission(QMicrophonePermission()) is Qt.PermissionStatus.Denied:
            self._pending_recording = None
            QMessageBox.warning(
                self,
                "Permissão de microfone negada",
                "Autorize o acesso ao microfone nas configurações de privacidade do sistema.",
            )
            return
        device, recording_format = self._pending_recording
        self._pending_recording = None
        try:
            self.recorder.start(device, None, recording_format)
        except (OSError, RuntimeError, ValueError) as error:
            QMessageBox.critical(self, "Falha ao iniciar gravação", str(error))

    def toggle_recording_pause(self) -> None:
        if self.recorder.state is RecordingState.RECORDING:
            self.recorder.pause()
        elif self.recorder.state is RecordingState.PAUSED:
            self.recorder.resume()

    def _handle_recording_state(self, state: RecordingState) -> None:
        active = state in {
            RecordingState.STARTING,
            RecordingState.RECORDING,
            RecordingState.PAUSED,
        }
        recording = state in {RecordingState.RECORDING, RecordingState.PAUSED}
        finalizing = state is RecordingState.FINALIZING
        self.record_button.setEnabled(
            state is RecordingState.READY and bool(QMediaDevices.audioInputs())
        )
        self.pause_recording_button.setEnabled(recording)
        self.stop_recording_button.setEnabled(active)
        self.pause_recording_button.setText(
            "Retomar" if state is RecordingState.PAUSED else "Pausar"
        )
        pause_icon = (
            QStyle.StandardPixmap.SP_MediaPlay
            if state is RecordingState.PAUSED
            else QStyle.StandardPixmap.SP_MediaPause
        )
        self.pause_recording_button.setIcon(self.style().standardIcon(pause_icon))
        self.microphone_combo.setEnabled(state is RecordingState.READY)
        self.recording_format_combo.setEnabled(state is RecordingState.READY)
        self.refresh_microphones_button.setEnabled(state is RecordingState.READY)
        self.save_audio_button.setEnabled(
            state is RecordingState.READY and self._recording_result is not None
        )
        self.drop_zone.setEnabled(state is RecordingState.READY and self.worker is None)
        self._refresh_transcribe_enabled()
        self._set_quality_controls_enabled(state is RecordingState.READY and self.worker is None)
        messages = {
            RecordingState.READY: "Gravação pronta.",
            RecordingState.STARTING: (
                "Ativando o microfone... aguarde o indicador Gravando antes de falar."
            ),
            RecordingState.RECORDING: "● Gravando áudio localmente em tempo real...",
            RecordingState.PAUSED: "Gravação pausada; o intervalo não será incluído.",
            RecordingState.FINALIZING: "Finalizando e convertendo o áudio com segurança...",
        }
        self.recording_status.setText(messages[state])
        if finalizing:
            self._handle_progress(-1)

    def _handle_recording_elapsed(self, seconds: float) -> None:
        self.recording_timer.setText(MarkdownExporter.format_timestamp(seconds))

    def _handle_recording_level(self, level: float) -> None:
        self.level_meter.setValue(round(level * 100))
        if level >= 0.98:
            self.recording_status.setText("● Gravando — possível clipping; reduza o ganho.")
        elif 0 < level < 0.05:
            self.recording_status.setText("● Gravando — sinal baixo; aproxime o microfone.")

    def _handle_recording_completed(self, result: RecordingResult) -> None:
        self._handle_progress(0)
        self._recording_result = result
        self._recording_saved = False
        self.selected_audio = result.final_path
        self.drop_zone.set_file(result.final_path)
        self._set_player_source(result.final_path)
        self._transcription_temporary = result.transcription_path
        warning = f" Avisos: {' '.join(result.warnings)}" if result.warnings else ""
        self.status_label.setText(
            "Gravação concluída e mantida temporariamente. "
            "Escolha Salvar áudio como... ou Iniciar transcrição."
            f"{warning}"
        )
        self._refresh_transcribe_enabled()
        self.save_audio_button.setEnabled(True)

    def save_recording_audio(self) -> None:
        result = self._recording_result
        if result is None or not result.final_path.is_file():
            return
        suggestion = Path.home() / f"gravacao{result.recording_format.extension}"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Salvar áudio gravado",
            str(suggestion),
            f"{result.recording_format.label} (*{result.recording_format.extension})",
        )
        if not path:
            return
        destination = Path(path)
        if destination.suffix.lower() != result.recording_format.extension:
            destination = destination.with_suffix(result.recording_format.extension)
        if destination.exists() and not self._confirm_overwrite(destination):
            return
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(result.final_path, destination)
        except OSError as error:
            QMessageBox.critical(
                self, "Falha ao salvar áudio", f"Não foi possível salvar a gravação: {error}"
            )
            return
        self._recording_saved = True
        self.selected_audio = destination.resolve()
        self.drop_zone.set_file(self.selected_audio)
        self._set_player_source(self.selected_audio)
        self.status_label.setText(f"Áudio salvo em {self.selected_audio}.")

    def _handle_recording_failure(self, message: str, recovery_path: object) -> None:
        self._handle_progress(0)
        self.status_label.setText(message)
        recovery = Path(recovery_path) if recovery_path else None
        if recovery and recovery.is_file():
            answer = QMessageBox.question(
                self,
                "Recuperar áudio sem perdas",
                f"{message}\n\nDeseja salvar a captura WAV recuperável?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if answer is QMessageBox.StandardButton.Yes:
                target, _ = QFileDialog.getSaveFileName(
                    self, "Salvar WAV recuperado", "gravacao-recuperada.wav", "WAV (*.wav)"
                )
                if target:
                    destination = Path(target).with_suffix(".wav")
                    shutil.copy2(recovery, destination)
                    self.status_label.setText(f"Áudio recuperado em {destination.name}.")
                    self.recorder.release_temporary(recovery)
            else:
                self.recorder.release_temporary(recovery)
        else:
            QMessageBox.critical(self, "Falha na gravação", message)

    def _transcription_options(self) -> TranscriptionOptions:
        return TranscriptionOptions(
            model_name=str(self.model_combo.currentData()),
            initial_prompt=self.context_input.text(),
            selective_review=self.selective_review_checkbox.isChecked(),
            priority=TranscriptionPriority(str(self.priority_combo.currentData())),
        )

    def _update_priority_state(self, *_args: Any) -> None:
        priority = TranscriptionPriority(str(self.priority_combo.currentData()))
        tooltip = self.priority_combo.currentData(Qt.ItemDataRole.ToolTipRole)
        self.priority_combo.setToolTip(str(tooltip or ""))
        maximum_fidelity = priority is TranscriptionPriority.MAX_FIDELITY
        if maximum_fidelity:
            self.selective_review_checkbox.setChecked(True)
        self.selective_review_checkbox.setEnabled(
            self.worker is None and not maximum_fidelity
        )
        self.selective_review_checkbox.setToolTip(
            "Incluída obrigatoriamente na prioridade de maior fidelidade."
            if maximum_fidelity
            else "Executa uma segunda passagem apenas em trechos de baixa confiança; "
            "pode aumentar o tempo."
        )

    def start_transcription(
        self,
        *,
        audio_path: str | Path | None = None,
        public_source_name: str | None = None,
        recording_metadata: dict[str, Any] | None = None,
    ) -> None:
        if audio_path is not None:
            source = Path(audio_path)
        elif self._recording_result is not None:
            source = self._recording_result.transcription_path
            public_source_name = public_source_name or self.selected_audio.name
            recording_metadata = (
                recording_metadata or self._recording_result.transcription_metadata
            )
        else:
            source = self.selected_audio
        if (
            source is None
            or self.worker is not None
            or self.recorder.state is not RecordingState.READY
        ):
            return
        if not self._model_ready():
            QMessageBox.information(
                self,
                "Modelo indisponível",
                "Escolha um modelo Offline ou use Baixar modelo antes de transcrever.",
            )
            self._update_model_state()
            return
        self.source_editor.clear()
        self.preview.clear()
        self.log_viewer.clear()
        self.copy_button.setEnabled(False)
        self.save_button.setEnabled(False)
        self.transcribe_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.drop_zone.setEnabled(False)
        self.record_button.setEnabled(False)
        self._transcription_failed = False
        self._transcription_cancelled = False
        self._transcription_started_at = time.monotonic()
        self._model_release_timer.stop()
        self._transcription_elapsed_seconds = 0.0
        self._active_processing_device = None
        self._gpu_utilization = None
        self._gpu_memory_used_mb = None
        self._gpu_memory_total_mb = None
        self._update_telemetry()
        self.coverage_label.setText("Cobertura em análise durante a transcrição...")
        self.worker = TranscriberWorker(
            source,
            self,
            options=self._transcription_options(),
            public_source_name=public_source_name,
            recording_metadata=recording_metadata,
        )
        self.worker.status_changed.connect(self._handle_status)
        self.worker.progress_changed.connect(self._handle_progress)
        self.worker.segment_decoded.connect(self._handle_segment)
        self.worker.completed.connect(self._handle_result)
        self.worker.failed.connect(self._handle_failure)
        self.worker.cancelled.connect(self._handle_cancelled)
        if hasattr(self.worker, "device_detected"):
            self.worker.device_detected.connect(self._handle_processing_device)
        self.worker.finished.connect(self._thread_finished)
        self.worker.finished.connect(self.worker.deleteLater)
        self._set_quality_controls_enabled(False)
        self.worker.start()

    def _set_quality_controls_enabled(self, enabled: bool) -> None:
        self.model_combo.setEnabled(enabled and self.model_download_worker is None)
        self.context_input.setEnabled(enabled)
        self.priority_combo.setEnabled(enabled)
        self._update_priority_state()
        self._update_model_state()

    def cancel_transcription(self) -> None:
        if self.worker is None or not self.worker.isRunning():
            return
        self.cancel_button.setEnabled(False)
        self.status_label.setText(
            "Cancelamento solicitado; finalizando a etapa atual com segurança..."
        )
        self.worker.cancel()

    def _handle_processing_device(self, device: str, description: str) -> None:
        self._active_processing_device = device
        self.device_label.setText(f"Processamento em uso: {description}")
        self._update_telemetry()

    def _update_telemetry(self) -> None:
        snapshot = self._resource_sampler.sample()
        if self._transcription_started_at is not None:
            elapsed = time.monotonic() - self._transcription_started_at
        else:
            elapsed = self._transcription_elapsed_seconds
        if self._active_processing_device == "cuda":
            if self._gpu_utilization is None:
                gpu_text = "GPU total: medindo...  •  VRAM: medindo..."
            else:
                gpu_text = (
                    f"GPU total: {self._gpu_utilization}%  •  VRAM: "
                    f"{self._gpu_memory_used_mb}/{self._gpu_memory_total_mb} MB"
                )
            self._start_gpu_probe()
        elif self._active_processing_device in {"rocm", "xpu"}:
            gpu_text = "GPU: ativa (telemetria indisponível)  •  VRAM: —"
        elif self._active_processing_device == "cpu":
            gpu_text = "GPU: não utilizada  •  VRAM: —"
        else:
            gpu_text = "GPU: aguardando transcrição  •  VRAM: —"
        self.telemetry_label.setText(
            f"Tempo: {MarkdownExporter.format_timestamp(elapsed)}  •  "
            f"CPU do app: {snapshot.cpu_percent:.1f}%  •  "
            f"RAM do app: {snapshot.ram_mb:.0f} MB  •  {gpu_text}"
        )

    def _start_gpu_probe(self) -> None:
        if (
            not self._nvidia_smi
            or self._gpu_probe.state() != QProcess.ProcessState.NotRunning
        ):
            return
        self._gpu_probe.setProgram(self._nvidia_smi)
        self._gpu_probe.setArguments(
            [
                "--query-gpu=utilization.gpu,memory.used,memory.total",
                "--format=csv,noheader,nounits",
            ]
        )
        self._gpu_probe.start()

    def _read_gpu_probe(self) -> None:
        output = bytes(self._gpu_probe.readAllStandardOutput()).decode(
            "utf-8", errors="replace"
        )
        first_line = output.strip().splitlines()[0] if output.strip() else ""
        try:
            utilization, used, total = (
                int(part.strip()) for part in first_line.split(",")[:3]
            )
        except (TypeError, ValueError):
            return
        self._gpu_utilization = max(0, min(100, utilization))
        self._gpu_memory_used_mb = max(0, used)
        self._gpu_memory_total_mb = max(0, total)

    def _handle_status(self, message: str) -> None:
        self.status_label.setText(message)
        self.log_viewer.appendPlainText(message)

    def _handle_progress(self, value: int) -> None:
        if value < 0:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(3)
            self.progress_bar.setFormat("Preparando...")
        else:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setFormat("%p%")
            self.progress_bar.setValue(value)

    def _handle_segment(self, text: str) -> None:
        self.log_viewer.appendPlainText(f"Trecho: {text}")

    def _handle_result(self, result: TranscriptionResult) -> None:
        markdown = MarkdownExporter.render(result)
        self.device_label.setText(
            f"Processamento usado: {TranscriberWorker.device_description(result.device)}"
        )
        self.source_editor.setPlainText(markdown)
        self.copy_button.setEnabled(True)
        self.save_button.setEnabled(True)
        self.tabs.setCurrentIndex(1)
        duration = MarkdownExporter.format_timestamp(result.duration_seconds)
        confidence = (
            f" Confiança média: {result.average_word_confidence * 100:.1f}% em "
            f"{result.word_count} palavras; {result.low_confidence_word_count} para revisão."
            if result.average_word_confidence is not None
            else " Confiança por palavra indisponível."
        )
        review = (
            f" {result.reviewed_segment_count} segmento(s) revisado(s) automaticamente."
            if result.reviewed_segment_count
            else ""
        )
        hallucinations = (
            f" {result.suspected_hallucination_count} possível(is) alucinação(ões) destacada(s)."
            if result.suspected_hallucination_count
            else ""
        )
        discarded = (
            f" {result.discarded_silence_segment_count} hipótese(s) sobre silêncio "
            "efetivo descartada(s)."
            if result.discarded_silence_segment_count
            else ""
        )
        self.coverage_label.setText(
            f"Cobertura: {result.processing_coverage_percent:.0f}% ({duration})."
            f"{confidence}{review}{hallucinations}{discarded}"
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
        self.coverage_label.setText("Transcrição interrompida; o áudio original foi preservado.")

    def _thread_finished(self) -> None:
        if self._transcription_started_at is not None:
            self._transcription_elapsed_seconds = (
                time.monotonic() - self._transcription_started_at
            )
            self._transcription_started_at = None
        self.worker = None
        self.cancel_button.setEnabled(False)
        self.drop_zone.setEnabled(True)
        self._refresh_transcribe_enabled()
        self.record_button.setEnabled(bool(QMediaDevices.audioInputs()))
        self._set_quality_controls_enabled(True)
        if (
            not self._transcription_failed
            and not self._transcription_cancelled
            and self.source_editor.toPlainText()
        ):
            self._handle_progress(100)
        self._update_telemetry()
        if self._transcription_failed or self._transcription_cancelled:
            self._release_transcriber_model()
        else:
            self._model_release_timer.start()

    def _release_idle_model(self) -> None:
        if self.worker is not None:
            return
        if self._release_transcriber_model():
            self.status_label.setText(
                "Modelo liberado após inatividade; RAM e VRAM foram recuperadas."
            )
            self._update_telemetry()

    @staticmethod
    def _release_transcriber_model() -> bool:
        release = getattr(TranscriberWorker, "release_cached_model", None)
        return bool(release()) if callable(release) else False

    def _discard_cached_recording(self) -> None:
        if self._recording_result is None and self._transcription_temporary is None:
            self.recorder.discard_cached_recording()
            return
        cached_paths = {
            path.resolve()
            for path in (
                self._recording_result.final_path if self._recording_result else None,
                self._transcription_temporary,
            )
            if path is not None
        }
        current_source = Path(self.player.source().toLocalFile()).resolve() if (
            self.player.source().isLocalFile() and self.player.source().toLocalFile()
        ) else None
        if current_source in cached_paths:
            self.player.stop()
            self.player.setSource(QUrl())
            self.player_button.setEnabled(False)
            self.player_slider.setEnabled(False)
        self.recorder.discard_cached_recording()
        self._recording_result = None
        self._recording_saved = False
        self._transcription_temporary = None
        self.save_audio_button.setEnabled(False)

    def update_preview(self) -> None:
        self.preview.setMarkdown(self.source_editor.toPlainText())

    def _set_player_source(self, path: Path) -> None:
        self.player.setSource(QUrl.fromLocalFile(str(path)))
        self.player_button.setEnabled(True)
        self.player_slider.setEnabled(True)

    def toggle_playback(self) -> None:
        if self.player.playbackState() is QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def _update_player_button(self, state: QMediaPlayer.PlaybackState) -> None:
        playing = state is QMediaPlayer.PlaybackState.PlayingState
        self.player_button.setText("Pausar" if playing else "Reproduzir")
        icon = (
            QStyle.StandardPixmap.SP_MediaPause
            if playing
            else QStyle.StandardPixmap.SP_MediaPlay
        )
        self.player_button.setIcon(self.style().standardIcon(icon))

    def _update_player_duration(self, duration: int) -> None:
        self.player_slider.setRange(0, max(0, duration))
        self._update_player_position(self.player.position())

    def _update_player_position(self, position: int) -> None:
        if not self.player_slider.isSliderDown():
            self.player_slider.setValue(position)
        self.player_time.setText(
            f"{self._format_player_time(position)} / "
            f"{self._format_player_time(self.player.duration())}"
        )

    @staticmethod
    def _format_player_time(milliseconds: int) -> str:
        seconds = max(0, milliseconds // 1000)
        minutes, secs = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}" if hours else f"{minutes:02d}:{secs:02d}"

    def _handle_preview_link(self, url: QUrl) -> None:
        if url.scheme() != "audio":
            return
        try:
            seconds = float(url.path().strip("/") or url.host())
        except ValueError:
            return
        self.player.setPosition(round(seconds * 1000))
        self.player.play()

    def copy_markdown(self) -> None:
        markdown = self.source_editor.toPlainText()
        if markdown:
            QApplication.clipboard().setText(markdown)
            self.status_label.setText("Markdown copiado para a área de transferência.")

    def save_markdown(self) -> None:
        if not self.source_editor.toPlainText() or self.selected_audio is None:
            return
        suggestion = self.selected_audio.with_name(f"{self.selected_audio.stem}_transcricao.md")
        path, _ = QFileDialog.getSaveFileName(
            self, "Salvar transcrição em Markdown", str(suggestion), "Markdown (*.md)"
        )
        if not path:
            return
        target = Path(path)
        if target.suffix.lower() != ".md":
            target = target.with_suffix(".md")
        if target.exists() and not self._confirm_overwrite(target):
            return
        try:
            saved = MarkdownExporter.save(self.source_editor.toPlainText(), target)
        except OSError as error:
            QMessageBox.critical(self, "Falha ao salvar", f"Não foi possível salvar: {error}")
            return
        self.status_label.setText(f"Transcrição salva em {saved.name}.")

    def _confirm_overwrite(self, target: Path) -> bool:
        answer = QMessageBox.question(
            self,
            "Confirmar substituição",
            f"O arquivo {target.name} já existe. Deseja substituí-lo?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return answer is QMessageBox.StandardButton.Yes

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        if self.model_download_worker is not None and self.model_download_worker.isRunning():
            QMessageBox.information(
                self,
                "Download em andamento",
                "Cancele o download do modelo e aguarde a confirmação antes de fechar.",
            )
            event.ignore()
            return
        if self.recorder.state in {
            RecordingState.STARTING,
            RecordingState.RECORDING,
            RecordingState.PAUSED,
        }:
            QMessageBox.information(
                self,
                "Gravação em andamento",
                "Pare e finalize a gravação antes de fechar o aplicativo.",
            )
            event.ignore()
            return
        if self.recorder.state is RecordingState.FINALIZING:
            QMessageBox.information(
                self, "Áudio em finalização", "Aguarde a conversão segura antes de fechar."
            )
            event.ignore()
            return
        if self.worker is not None and self.worker.isRunning():
            QMessageBox.information(
                self,
                "Transcrição em andamento",
                "Cancele a transcrição e aguarde a confirmação antes de fechar o aplicativo.",
            )
            event.ignore()
            return
        self._discard_cached_recording()
        self._model_release_timer.stop()
        self._release_transcriber_model()
        event.accept()
