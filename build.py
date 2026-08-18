"""Build reproduzível do executável único com PyInstaller."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from app.core.ffmpeg_finder import FFmpegFinder


def build(*, prepare_only: bool = False) -> Path:
    root = Path(__file__).resolve().parent
    platform_key = FFmpegFinder.platform_key()
    ffmpeg = FFmpegFinder.ensure_static(progress=lambda value: print(f"FFmpeg: {value}%"))
    print(f"FFmpeg verificado: {ffmpeg}")
    if prepare_only:
        return ffmpeg

    separator = os.pathsep
    icon = root / "assets" / ("icon.ico" if platform_key == "windows" else "icon.png")
    if not icon.is_file():
        raise FileNotFoundError(f"Ícone obrigatório não encontrado: {icon}")

    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",
        "--name",
        "WhisperTranscriber",
        "--icon",
        str(icon),
        "--add-binary",
        f"{ffmpeg}{separator}assets/ffmpeg/{platform_key}",
        "--add-data",
        f"{root / 'assets' / 'icon.png'}{separator}assets",
        "--collect-all",
        "whisper",
        "--collect-all",
        "torch",
        "--hidden-import",
        "tiktoken_ext.openai_public",
        str(root / "main.py"),
    ]
    print("Iniciando compilação do executável único...")
    subprocess.run(command, cwd=root, check=True)
    executable = root / "dist" / (
        "WhisperTranscriber.exe" if platform_key == "windows" else "WhisperTranscriber"
    )
    if not executable.is_file():
        raise RuntimeError("O PyInstaller terminou sem gerar o executável esperado.")
    print(f"Compilação concluída: {executable}")
    return executable


def main() -> int:
    parser = argparse.ArgumentParser(description="Compila o Whisper Transcriber Desktop")
    parser.add_argument(
        "--prepare-ffmpeg",
        action="store_true",
        help="baixa e verifica o FFmpeg sem executar o PyInstaller",
    )
    args = parser.parse_args()
    build(prepare_only=args.prepare_ffmpeg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
