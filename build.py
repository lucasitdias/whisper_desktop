"""Build portátil e instalável do Whisper Transcriber Desktop."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from string import Template
from xml.etree import ElementTree

from app import __version__
from app.core.ffmpeg_finder import FFmpegFinder

APP_EXECUTABLE = "WhisperTranscriber"
INSTALLER_NAME = "WhisperTranscriber-Setup-Windows-x64.exe"
STORE_PACKAGE_NAME = "WhisperTranscriber.WhisperTranscriberDesktop"
STORE_PUBLISHER = "CN=B12A9AED-D3CC-463A-B3E5-ED71178CABF3"
STORE_PUBLISHER_DISPLAY_NAME = "WhisperTranscriber"
STORE_ID = "9PHWS6MM59BG"
# A versão técnica do pacote precisa ser monotônica no Partner Center. Ela é
# independente da versão pública 0.2.1 do aplicativo e da tag do GitHub.
STORE_PACKAGE_VERSION = "1.2.4.0"
MSIX_NAME = f"WhisperTranscriber-Desktop-{__version__}-Windows-x64.msix"


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
    require_runtime: str | None = None,
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
    cuda_detected = device.startswith(("GPU NVIDIA CUDA", "GPU CUDA"))
    if require_cuda and not cuda_detected:
        raise RuntimeError(f"O build deveria usar CUDA, mas detectou: {device or 'desconhecido'}")
    runtime = str(payload.get("runtime_pytorch", ""))
    if require_runtime and not runtime.casefold().startswith(require_runtime.casefold()):
        raise RuntimeError(
            f"O build deveria conter o runtime {require_runtime}, mas contém: "
            f"{runtime or 'desconhecido'}"
        )
    print(f"Executável verificado: {device}")
    if runtime:
        print(f"Runtime incorporado: {runtime}")
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


def find_makeappx() -> Path:
    """Localiza o empacotador MSIX oficial do Windows SDK."""
    configured = os.environ.get("MAKEAPPX_PATH")
    candidates = [Path(configured)] if configured else []
    from_path = shutil.which("makeappx.exe") or shutil.which("makeappx")
    if from_path:
        candidates.append(Path(from_path))
    program_files_x86 = os.environ.get("PROGRAMFILES(X86)")
    if program_files_x86:
        windows_kits = Path(program_files_x86) / "Windows Kits" / "10"
        candidates.append(windows_kits / "App Certification Kit" / "makeappx.exe")
        bin_dir = windows_kits / "bin"
        if bin_dir.is_dir():
            candidates.extend(
                sorted(bin_dir.glob("*/x64/makeappx.exe"), reverse=True)
            )
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    raise FileNotFoundError(
        "MakeAppx não encontrado. Instale o Windows SDK ou defina MAKEAPPX_PATH."
    )


def msix_version(version: str) -> str:
    """Converte a versão do projeto para os quatro campos exigidos pela Store."""
    parts = version.split(".")
    if not 1 <= len(parts) <= 3 or any(not part.isdigit() for part in parts):
        raise ValueError(f"Versão inválida para MSIX: {version}")
    numbers = [int(part) for part in parts]
    if any(number > 65535 for number in numbers):
        raise ValueError(f"Versão fora do intervalo permitido pelo MSIX: {version}")
    # A Store não aceita zero no primeiro campo. Projetos ainda em 0.x usam 1.x no pacote.
    numbers[0] = max(1, numbers[0])
    return ".".join(str(number) for number in (*numbers, *([0] * (4 - len(numbers)))))


def render_msix_manifest(destination: Path) -> Path:
    """Renderiza o manifesto com a identidade reservada no Partner Center."""
    root = Path(__file__).resolve().parent
    template_path = root / "store" / "AppxManifest.xml.in"
    if not template_path.is_file():
        raise FileNotFoundError(f"Modelo de manifesto MSIX não encontrado: {template_path}")
    content = Template(template_path.read_text(encoding="utf-8")).substitute(
        PACKAGE_NAME=STORE_PACKAGE_NAME,
        PUBLISHER=STORE_PUBLISHER,
        PUBLISHER_DISPLAY_NAME=STORE_PUBLISHER_DISPLAY_NAME,
        VERSION=STORE_PACKAGE_VERSION,
        EXECUTABLE=f"{APP_EXECUTABLE}.exe",
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(content, encoding="utf-8", newline="\n")
    ElementTree.parse(destination)
    return destination


def generate_msix_assets(destination: Path) -> list[Path]:
    """Gera os PNGs nas dimensões obrigatórias da Store."""
    from PIL import Image

    root = Path(__file__).resolve().parent
    source = root / "assets" / "icon.png"
    if not source.is_file():
        raise FileNotFoundError(f"Ícone obrigatório não encontrado: {source}")
    destination.mkdir(parents=True, exist_ok=True)
    sizes = {
        "Square44x44Logo.png": (44, 44),
        "Square150x150Logo.png": (150, 150),
        "StoreLogo.png": (50, 50),
    }
    generated: list[Path] = []
    with Image.open(source) as image:
        image = image.convert("RGBA")
        for name, size in sizes.items():
            target = destination / name
            image.resize(size, Image.Resampling.LANCZOS).save(target, format="PNG")
            generated.append(target)
    return generated


def _hardlink_or_copy(source: str, destination: str) -> str:
    """Evita duplicar vários gigabytes durante o estágio local do MSIX."""
    try:
        os.link(source, destination)
        return destination
    except OSError:
        return shutil.copy2(source, destination)


def _third_party_notice() -> Path:
    root = Path(__file__).resolve().parent
    candidates = [root / "THIRD_PARTY_NOTICES.md", root / "docs" / "THIRD_PARTY_NOTICES.md"]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("THIRD_PARTY_NOTICES.md não foi encontrado.")


def build_msix(executable: Path) -> Path:
    """Empacota o diretório PyInstaller como MSIX não assinado para a Store."""
    if not sys.platform.startswith("win"):
        raise RuntimeError("O pacote MSIX só pode ser compilado no Windows.")
    if not executable.is_file() or executable.parent.name != APP_EXECUTABLE:
        raise ValueError("O MSIX exige o build PyInstaller no modo --onedir.")

    root = Path(__file__).resolve().parent
    output_dir = root / "dist" / "store"
    output_dir.mkdir(parents=True, exist_ok=True)
    package = output_dir / MSIX_NAME
    staging_parent = root / "build"
    staging_parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="whisper-msix-", dir=staging_parent) as temporary:
        stage = Path(temporary) / "package"
        shutil.copytree(executable.parent, stage, copy_function=_hardlink_or_copy)
        render_msix_manifest(stage / "AppxManifest.xml")
        generate_msix_assets(stage / "Assets")
        shutil.copy2(_third_party_notice(), stage / "THIRD_PARTY_NOTICES.md")
        command = [
            str(find_makeappx()),
            "pack",
            "/d",
            str(stage),
            "/p",
            str(package),
            "/o",
            "/h",
            "SHA256",
        ]
        print("Compilando o pacote MSIX para a Microsoft Store...")
        result = subprocess.run(
            command,
            cwd=root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        output_lines = [line for line in result.stdout.splitlines() if line.strip()]
        if output_lines:
            print(output_lines[-1])

    if not package.is_file():
        raise RuntimeError("O MakeAppx terminou sem gerar o pacote esperado.")
    print(f"MSIX concluído: {package}")
    return package


def verify_msix(package: Path) -> dict[str, str]:
    """Confere identidade, versão e executável sem extrair o MSIX inteiro."""
    if not package.is_file():
        raise FileNotFoundError(f"Pacote MSIX não encontrado: {package}")
    with zipfile.ZipFile(package) as archive:
        names = set(archive.namelist())
        if "AppxManifest.xml" not in names:
            raise RuntimeError("O MSIX não contém o manifesto obrigatório.")
        tree = ElementTree.ElementTree(ElementTree.fromstring(archive.read("AppxManifest.xml")))
        namespace = {"p": "http://schemas.microsoft.com/appx/manifest/foundation/windows10"}
        identity = tree.find("p:Identity", namespace)
        if identity is None:
            raise RuntimeError("O MSIX não contém a identidade obrigatória.")
        expected = {
            "Name": STORE_PACKAGE_NAME,
            "Publisher": STORE_PUBLISHER,
            "Version": STORE_PACKAGE_VERSION,
            "ProcessorArchitecture": "x64",
        }
        actual = {key: identity.get(key, "") for key in expected}
        if actual != expected:
            raise RuntimeError(f"Identidade MSIX divergente: {actual}")
        if f"{APP_EXECUTABLE}.exe" not in names:
            raise RuntimeError("O executável principal não foi incluído no MSIX.")
    print(f"MSIX verificado para a Store {STORE_ID}: {actual['Version']}")
    return actual


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
        "--installer-cpu",
        action="store_true",
        help="gera o instalador Windows offline com PyTorch CPU para distribuição",
    )
    mode.add_argument(
        "--installer-only",
        action="store_true",
        help="compila apenas o instalador usando o diretório dist existente",
    )
    mode.add_argument(
        "--msix",
        action="store_true",
        help="gera o aplicativo CUDA e o MSIX para envio à Microsoft Store",
    )
    mode.add_argument(
        "--msix-only",
        action="store_true",
        help="gera apenas o MSIX usando o diretório dist existente",
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
        verify_executable(
            executable,
            require_cuda=True,
            require_runtime="NVIDIA CUDA",
            allow_policy_block=True,
        )
        build_installer(executable)
        return 0
    if args.installer_cpu:
        executable = build(onefile=False)
        verify_executable(executable, require_runtime="CPU")
        build_installer(executable)
        return 0
    if args.msix_only:
        executable = (
            Path(__file__).resolve().parent
            / "dist"
            / APP_EXECUTABLE
            / f"{APP_EXECUTABLE}.exe"
        )
        package = build_msix(executable)
        verify_msix(package)
        return 0
    if args.msix:
        executable = build(onefile=False)
        verify_executable(
            executable,
            require_cuda=True,
            require_runtime="NVIDIA CUDA",
            allow_policy_block=True,
        )
        package = build_msix(executable)
        verify_msix(package)
        return 0
    executable = build(onefile=True)
    verify_executable(executable)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
