"""Ponto de entrada do Whisper Transcriber Desktop."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import TextIO

from app import __version__

_NULL_STREAMS: list[TextIO] = []


def resource_path(relative: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / relative


def ensure_standard_streams() -> None:
    """Fornece streams graváveis quando o PyInstaller é executado com ``--windowed``."""
    for stream_name in ("stdout", "stderr"):
        if getattr(sys, stream_name) is None:
            stream = open(os.devnull, "w", encoding="utf-8")  # noqa: SIM115
            setattr(sys, stream_name, stream)
            _NULL_STREAMS.append(stream)


def self_check(output_path: str | Path | None = None) -> int:
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
        serialized = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        if output_path is not None:
            destination = Path(output_path)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(serialized, encoding="utf-8")
        if sys.stdout is not None:
            sys.stdout.write(serialized)
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
    ensure_standard_streams()
    parser = argparse.ArgumentParser(description="Whisper Transcriber Desktop")
    parser.add_argument(
        "--self-check",
        action="store_true",
        help="valida dependências e FFmpeg sem abrir a interface",
    )
    parser.add_argument(
        "--self-check-output",
        metavar="ARQUIVO",
        help="grava o resultado JSON da autoverificação no arquivo informado",
    )
    args = parser.parse_args()
    if args.self_check or args.self_check_output:
        return self_check(args.self_check_output)
    return run_gui()


if __name__ == "__main__":
    raise SystemExit(main())
