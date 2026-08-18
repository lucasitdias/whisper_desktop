"""Build portátil e instalável do Whisper Transcriber Desktop."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from app import __version__
from app.core.ffmpeg_finder import FFmpegFinder

APP_EXECUTABLE = "WhisperTranscriber"
INSTALLER_NAME = "WhisperTranscriber-Setup-Windows-x64.exe"


def build(*, onefile: bool = True, prepare_only: bool = False) -> Path:
    """Compila o aplicativo, em arquivo único ou diretório para o instalador."""
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
        "--onefile" if onefile else "--onedir",
        "--windowed",
        "--name",
        APP_EXECUTABLE,
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
    mode = "arquivo único" if onefile else "diretório instalável"
    print(f"Iniciando compilação do {mode}...")
    subprocess.run(command, cwd=root, check=True)
    suffix = ".exe" if platform_key == "windows" else ""
    executable = root / "dist" / f"{APP_EXECUTABLE}{suffix}"
    if not onefile:
        executable = root / "dist" / APP_EXECUTABLE / f"{APP_EXECUTABLE}{suffix}"
    if not executable.is_file():
        raise RuntimeError("O PyInstaller terminou sem gerar o executável esperado.")
    print(f"Compilação concluída: {executable}")
    return executable


def verify_executable(
    executable: Path,
    *,
    require_cuda: bool = False,
    allow_policy_block: bool = False,
) -> dict[str, str]:
    """Executa a autoverificação do artefato sem depender de uma janela de console."""
    with tempfile.TemporaryDirectory(prefix="whisper-self-check-") as temporary:
        output = Path(temporary) / "resultado.json"
        try:
            subprocess.run(
                [str(executable), "--self-check-output", str(output)],
                check=True,
                timeout=300,
                creationflags=(
                    subprocess.CREATE_NO_WINDOW if sys.platform.startswith("win") else 0
                ),
            )
        except OSError as error:
            if allow_policy_block and getattr(error, "winerror", None) == 4551:
                print(
                    "Aviso: o Smart App Control bloqueou a autoverificação do binário "
                    "local sem assinatura. O instalador ainda será compilado."
                )
                return {"status": "bloqueado_politica", "dispositivo": "não verificado"}
            raise
        payload = json.loads(output.read_text(encoding="utf-8"))
    if payload.get("status") != "ok":
        raise RuntimeError("A autoverificação do executável não retornou status ok.")
    device = str(payload.get("dispositivo", ""))
    if require_cuda and not device.startswith("GPU CUDA"):
        raise RuntimeError(f"O build deveria usar CUDA, mas detectou: {device or 'desconhecido'}")
    print(f"Executável verificado: {device}")
    return payload


def find_iscc() -> Path:
    """Localiza o compilador do Inno Setup instalado no Windows."""
    configured = os.environ.get("ISCC_PATH")
    candidates = [Path(configured)] if configured else []
    from_path = shutil.which("ISCC.exe") or shutil.which("ISCC")
    if from_path:
        candidates.append(Path(from_path))
    for environment_name in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA"):
        base = os.environ.get(environment_name)
        if not base:
            continue
        candidates.extend(
            [
                Path(base) / "Inno Setup 7" / "ISCC.exe",
                Path(base) / "Programs" / "Inno Setup 7" / "ISCC.exe",
                Path(base) / "Inno Setup 6" / "ISCC.exe",
                Path(base) / "Programs" / "Inno Setup 6" / "ISCC.exe",
            ]
        )
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    raise FileNotFoundError(
        "Inno Setup não encontrado. Instale-o ou defina ISCC_PATH com o caminho do ISCC.exe."
    )


def build_installer(executable: Path) -> Path:
    """Empacota o diretório PyInstaller em um instalador Windows com desinstalador."""
    if not sys.platform.startswith("win"):
        raise RuntimeError("O instalador Inno Setup só pode ser compilado no Windows.")
    if not executable.is_file():
        raise FileNotFoundError(f"Executável do aplicativo não encontrado: {executable}")
    source_dir = executable.parent
    if executable.parent.name != APP_EXECUTABLE:
        raise ValueError("O instalador exige o build PyInstaller no modo --onedir.")
    root = Path(__file__).resolve().parent
    script = root / "installer" / "WhisperTranscriber.iss"
    if not script.is_file():
        raise FileNotFoundError(f"Script do instalador não encontrado: {script}")
    output_dir = root / "dist" / "installer"
    output_dir.mkdir(parents=True, exist_ok=True)
    installer = output_dir / INSTALLER_NAME
    command = [
        str(find_iscc()),
        "/Qp",
        f"/O{output_dir}",
        f"/DAppVersion={__version__}",
        f"/DSourceDir={source_dir}",
        f"/DRootDir={root}",
        str(script),
    ]
    print("Compilando o instalador Windows...")
    subprocess.run(command, cwd=root, check=True)
    if not installer.is_file():
        raise RuntimeError("O Inno Setup terminou sem gerar o instalador esperado.")
    print(f"Instalador concluído: {installer}")
    return installer


def main() -> int:
    parser = argparse.ArgumentParser(description="Compila o Whisper Transcriber Desktop")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--prepare-ffmpeg",
        action="store_true",
        help="baixa e verifica o FFmpeg sem executar o PyInstaller",
    )
    mode.add_argument(
        "--installer",
        action="store_true",
        help="gera o aplicativo CUDA em diretório e o instalador Windows",
    )
    mode.add_argument(
        "--installer-only",
        action="store_true",
        help="compila apenas o instalador usando o diretório dist existente",
    )
    args = parser.parse_args()
    if args.prepare_ffmpeg:
        build(prepare_only=True)
        return 0
    if args.installer_only:
        executable = (
            Path(__file__).resolve().parent
            / "dist"
            / APP_EXECUTABLE
            / f"{APP_EXECUTABLE}.exe"
        )
        build_installer(executable)
        return 0
    if args.installer:
        executable = build(onefile=False)
        verify_executable(executable, require_cuda=True, allow_policy_block=True)
        build_installer(executable)
        return 0
    executable = build(onefile=True)
    verify_executable(executable)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
