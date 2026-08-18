"""Ponto de entrada do Whisper Transcriber Desktop."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app import __version__


def resource_path(relative: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / relative


def self_check() -> int:
    from app.core.ffmpeg_finder import FFmpegFinder
    from app.core.transcriber import TranscriberWorker

    try:
        ffmpeg = FFmpegFinder.ensure_available()
        payload = {
            "aplicativo": "Whisper Transcriber Desktop",
            "versao": __version__,
            "python": sys.version.split()[0],
            "ffmpeg": str(ffmpeg),
            "dispositivo": TranscriberWorker.device_description(),
            "status": "ok",
        }
        if sys.stdout is not None:
            sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        return 0
    except Exception as error:
        if sys.stderr is not None:
            sys.stderr.write(f"Autoverificação falhou: {error}\n")
        return 1


def run_gui() -> int:
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication

    from app.ui.main_window import MainWindow
    from app.ui.styles import DARK_THEME_QSS

    app = QApplication(sys.argv)
    app.setApplicationName("Whisper Transcriber Desktop")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("Whisper Transcriber")
    icon = resource_path("assets/icon.png")
    if icon.is_file():
        app.setWindowIcon(QIcon(str(icon)))
    app.setStyleSheet(DARK_THEME_QSS)
    window = MainWindow()
    window.show()
    return app.exec()


def main() -> int:
    parser = argparse.ArgumentParser(description="Whisper Transcriber Desktop")
    parser.add_argument(
        "--self-check",
        action="store_true",
        help="valida dependências e FFmpeg sem abrir a interface",
    )
    args = parser.parse_args()
    return self_check() if args.self_check else run_gui()


if __name__ == "__main__":
    raise SystemExit(main())
