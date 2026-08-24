"""Validação manual opt-in de captura real e encoding no microfone padrão."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PySide6.QtCore import QObject, QTimer
from PySide6.QtMultimedia import QMediaDevices
from PySide6.QtWidgets import QApplication

from app.core.recorder import RECORDING_FORMATS, RecorderController, RecordingResult


class ValidationHarness(QObject):
    def __init__(self, destination: Path, format_key: str, duration: float) -> None:
        super().__init__()
        self.destination = destination
        self.recording_format = next(item for item in RECORDING_FORMATS if item.key == format_key)
        self.duration = duration
        self.exit_code = 1
        self.controller = RecorderController(self)
        self.controller.completed.connect(self._completed)
        self.controller.failed.connect(self._failed)

    def start(self) -> None:
        try:
            device = QMediaDevices.defaultAudioInput()
            if device.isNull():
                raise OSError("Nenhum microfone padrão foi encontrado.")
            self.controller.start(device, self.destination, self.recording_format)
            QTimer.singleShot(round(self.duration * 1000), self.controller.stop)
        except (OSError, RuntimeError, ValueError) as error:
            self._failed(str(error), None)

    def _completed(self, result: RecordingResult) -> None:
        payload = {
            "status": "ok",
            "device": result.device_name,
            "format": result.recording_format.label,
            "path": str(result.final_path),
            "bytes": result.final_path.stat().st_size,
            "duration_seconds": result.duration_seconds,
            "peak_dbfs": result.peak_dbfs,
            "warnings": result.warnings,
        }
        print(json.dumps(payload, ensure_ascii=False))
        self.controller.release_temporary(result.transcription_path)
        self.exit_code = 0
        QApplication.instance().quit()

    def _failed(self, message: str, recovery_path: object) -> None:
        print(
            json.dumps(
                {
                    "status": "error",
                    "message": message,
                    "recovery_path": str(recovery_path) if recovery_path else None,
                },
                ensure_ascii=False,
            )
        )
        QApplication.instance().quit()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--format", choices=[item.key for item in RECORDING_FORMATS], required=True)
    parser.add_argument("--duration", type=float, default=2.0)
    args = parser.parse_args()
    app = QApplication([])
    harness = ValidationHarness(args.destination, args.format, args.duration)
    QTimer.singleShot(0, harness.start)
    app.exec()
    return harness.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
