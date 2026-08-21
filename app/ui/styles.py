"""Folha de estilos global do tema escuro."""

DARK_THEME_QSS = """
QMainWindow, QWidget {
    background-color: #121214;
    color: #F3F4F6;
    font-family: 'Segoe UI', 'Inter', sans-serif;
    font-size: 13px;
}
QLabel#titleLabel { font-size: 20px; font-weight: 700; color: #F3F4F6; }
QLabel#sectionLabel { font-size: 15px; font-weight: 600; color: #F3F4F6; }
QLabel#mutedLabel, QLabel#deviceLabel { color: #9CA3AF; font-size: 11px; }
QLabel#statusLabel { color: #F3F4F6; font-size: 11px; }
QFrame#cardPanel {
    background-color: #1E1E24;
    border: 1px solid #2C2C35;
    border-radius: 8px;
}
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
    border-radius: 6px;
    padding: 10px 20px;
}
QPushButton#primaryButton:hover { background-color: #4F46E5; }
QPushButton#primaryButton:pressed { background-color: #4338CA; }
QPushButton#primaryButton:disabled { background-color: #374151; color: #9CA3AF; }
QPushButton#secondaryButton {
    background-color: transparent;
    color: #F3F4F6;
    border: 1px solid #374151;
    border-radius: 6px;
    padding: 8px 16px;
}
QPushButton#secondaryButton:hover { background-color: #2C2C35; }
QPushButton#secondaryButton:disabled { color: #4B5563; border-color: #2C2C35; }
QPushButton#dangerButton {
    background-color: transparent;
    color: #FCA5A5;
    border: 1px solid #EF4444;
    border-radius: 6px;
    padding: 9px 16px;
}
QPushButton#dangerButton:hover { background-color: #3F1D24; color: #FFFFFF; }
QPushButton#dangerButton:pressed { background-color: #5F1D28; }
QPushButton#dangerButton:disabled { color: #4B5563; border-color: #2C2C35; }
QTextEdit, QPlainTextEdit, QTextBrowser {
    background-color: #18181C;
    color: #F3F4F6;
    border: 1px solid #2C2C35;
    border-radius: 6px;
    padding: 8px;
    selection-background-color: #6366F1;
}
QPlainTextEdit#logViewer { font-family: 'Consolas', 'Fira Code', monospace; font-size: 12px; }
QProgressBar {
    background-color: #18181C;
    border: 1px solid #2C2C35;
    border-radius: 4px;
    text-align: center;
    color: #F3F4F6;
    min-height: 18px;
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
QToolTip { background-color: #1E1E24; color: #F3F4F6; border: 1px solid #2C2C35; }
"""
