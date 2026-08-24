"""Folha de estilos global do tema escuro."""

DARK_THEME_QSS = """
QMainWindow {
    background-color: #121214;
}
QWidget {
    color: #F3F4F6;
    font-family: 'Segoe UI', 'Inter', sans-serif;
    font-size: 11pt;
}
QScrollArea#mainScroll, QScrollArea#mainScroll > QWidget > QWidget, QWidget#contentPage {
    background-color: #121214;
}
QLabel#titleLabel { font-size: 18pt; font-weight: 700; color: #F9FAFB; }
QLabel#sectionLabel { font-size: 13pt; font-weight: 650; color: #F9FAFB; }
QLabel#mutedLabel, QLabel#deviceLabel { color: #B8C0CC; font-size: 10.5pt; }
QLabel#statusLabel { color: #F3F4F6; font-size: 10.5pt; }
QLabel#timerLabel { color: #FCA5A5; font-size: 13pt; font-weight: 700; }
QLabel#telemetryTitle { color: #F3F4F6; font-weight: 650; }
QLabel#telemetryLabel { color: #C7D2FE; font-size: 10.5pt; }
QLabel#modelStatusLabel { color: #C7D2FE; font-size: 10.5pt; }
QFrame#cardPanel {
    background-color: #1E1E24;
    border: 1px solid #2C2C35;
    border-radius: 8px;
}
QFrame#telemetryPanel {
    background: #17181E;
    border: 1px solid #343744;
    border-radius: 8px;
}
QFrame#resultPanel {
    background-color: #121214;
    border-top: 1px solid #2C2C35;
}
QSplitter#mainSplitter::handle {
    background-color: #343744;
    height: 7px;
}
QSplitter#mainSplitter::handle:hover { background-color: #6366F1; }
QFrame#dropZone {
    background-color: #1E1E24;
    border: 2px dashed #2C2C35;
    border-radius: 8px;
}
QFrame#dropZone[dragActive="true"] {
    background-color: #252533;
    border-color: #6366F1;
}
QPushButton#primaryButton {
    background-color: #6366F1;
    color: #FFFFFF;
    font-weight: bold;
    border: none;
    border-radius: 7px;
    padding: 9px 16px;
    min-height: 24px;
}
QPushButton#primaryButton:hover { background-color: #4F46E5; }
QPushButton#primaryButton:pressed { background-color: #4338CA; }
QPushButton#primaryButton:disabled { background-color: #374151; color: #9CA3AF; }
QPushButton#secondaryButton {
    background-color: transparent;
    color: #F3F4F6;
    border: 1px solid #374151;
    border-radius: 7px;
    padding: 8px 14px;
    min-height: 24px;
}
QPushButton#secondaryButton:hover { background-color: #2C2C35; }
QPushButton#secondaryButton:disabled { color: #4B5563; border-color: #2C2C35; }
QPushButton#dangerButton {
    background-color: transparent;
    color: #FCA5A5;
    border: 1px solid #EF4444;
    border-radius: 7px;
    padding: 8px 14px;
    min-height: 24px;
}
QPushButton#dangerButton:hover { background-color: #3F1D24; color: #FFFFFF; }
QPushButton#dangerButton:pressed { background-color: #5F1D28; }
QPushButton#dangerButton:disabled { color: #4B5563; border-color: #2C2C35; }
QPushButton#recordButton {
    background-color: #DC2626;
    color: #FFFFFF;
    font-weight: bold;
    border: none;
    border-radius: 7px;
    padding: 9px 16px;
    min-height: 24px;
}
QPushButton#recordButton:hover { background-color: #B91C1C; }
QPushButton#recordButton:disabled { background-color: #4B5563; color: #9CA3AF; }
QComboBox, QLineEdit {
    background-color: #18181C;
    color: #F3F4F6;
    border: 1px solid #374151;
    border-radius: 7px;
    padding: 7px 11px;
    min-height: 24px;
}
QComboBox:disabled, QLineEdit:disabled { color: #6B7280; border-color: #2C2C35; }
QComboBox QAbstractItemView {
    background-color: #1E1E24;
    color: #F3F4F6;
    selection-background-color: #4F46E5;
}
QPushButton#compactButton {
    background-color: transparent;
    color: #E5E7EB;
    border: 1px solid #374151;
    border-radius: 7px;
    padding: 8px 12px;
    min-height: 24px;
}
QPushButton#compactButton:hover { background-color: #2C2C35; border-color: #6366F1; }
QPushButton#compactButton:disabled { color: #6B7280; border-color: #2C2C35; }
QCheckBox { spacing: 8px; min-height: 28px; }
QSlider::groove:horizontal { height: 5px; background: #2C2C35; border-radius: 2px; }
QSlider::handle:horizontal {
    width: 14px; margin: -5px 0; background: #6366F1; border-radius: 7px;
}
QTextEdit, QPlainTextEdit, QTextBrowser {
    background-color: #18181C;
    color: #F3F4F6;
    border: 1px solid #2C2C35;
    border-radius: 6px;
    padding: 8px;
    selection-background-color: #6366F1;
}
QPlainTextEdit#logViewer { font-family: 'Consolas', 'Fira Code', monospace; font-size: 10.5pt; }
QProgressBar {
    background-color: #18181C;
    border: 1px solid #2C2C35;
    border-radius: 4px;
    text-align: center;
    color: #F3F4F6;
    min-height: 20px;
}
QProgressBar::chunk { background-color: #6366F1; border-radius: 3px; }
QTabWidget::pane { border: 1px solid #2C2C35; border-radius: 6px; }
QTabBar::tab {
    background: #18181C;
    color: #9CA3AF;
    border: 1px solid #2C2C35;
    padding: 8px 16px;
}
QTabBar::tab:selected { background: #1E1E24; color: #F3F4F6; border-bottom-color: #6366F1; }
QScrollBar:vertical { background-color: #121214; width: 8px; margin: 0; }
QScrollBar::handle:vertical { background-color: #2C2C35; min-height: 20px; border-radius: 4px; }
QScrollBar::handle:vertical:hover { background-color: #4B5563; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QToolTip {
    background-color: #252533;
    color: #F9FAFB;
    border: 1px solid #6366F1;
    padding: 7px;
    font-size: 10pt;
}
"""
