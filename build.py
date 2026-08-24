"""Build portátil e instalável do Whisper Transcriber Desktop."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path
from string import Template
from xml.etree import ElementTree

from app import __version__
from app.core.ffmpeg_finder import FFmpegFinder
from app.core.model_catalog import (
    BUNDLED_MODEL_IDS,
    MODEL_BY_ID,
    ModelManager,
    download_checkpoint,
)

APP_EXECUTABLE = "WhisperTranscriber"
INSTALLER_NAME = "WhisperTranscriber-Setup-Windows-x64.exe"
CPU_INSTALLER_NAME = "WhisperTranscriber-Setup-Windows-x64-CPU.exe"
WINDOWS_PORTABLE_NAME = "WhisperTranscriber-Windows-x64.zip"
LINUX_PORTABLE_NAME = "WhisperTranscriber-Linux-x64.tar.gz"
CUDA_INSTALLER_BUNDLE_NAME = "WhisperTranscriber-Setup-Windows-x64-Offline.zip"
CPU_INSTALLER_BUNDLE_NAME = "WhisperTranscriber-Setup-Windows-x64-CPU-Offline.zip"
STORE_PACKAGE_NAME = "WhisperTranscriberDesktop.WhisperTranscriberDeskto"
STORE_PUBLISHER = "CN=8D30778F-07F5-435C-A526-6B1646073081"
STORE_PUBLISHER_DISPLAY_NAME = "Lucas Dias"
STORE_ID = "9NJN8VV2N833"
# A versão técnica do pacote precisa ser monotônica no Partner Center. Ela é
# independente da versão pública do aplicativo e da tag do GitHub.
# A versão pública v0.3.0 usa 1.3.4.0 somente como versão técnica do MSIX local.
# O produto Pro terá identidade própria antes de qualquer envio ao Partner Center.
STORE_PACKAGE_VERSION = "1.3.4.0"
MSIX_NAME = f"WhisperTranscriber-Desktop-{__version__}-Windows-x64.msix"


def prepare_bundled_models() -> tuple[Path, ...]:
    """Garante e valida os checkpoints que devem seguir no pacote offline."""

    checkpoints: list[Path] = []
    for model_id in BUNDLED_MODEL_IDS:
        spec = MODEL_BY_ID[model_id]
        last_progress = -1

        def report_progress(value: int, *, name: str = model_id) -> None:
            nonlocal last_progress
            if value != last_progress:
                print(f"Modelo {name}: {value}%")
                last_progress = value

        checkpoint = download_checkpoint(
            spec,
            destination_root=ModelManager.cache_root(),
            progress=report_progress,
            status=print,
        )
        ModelManager.verify(checkpoint, spec)
        checkpoints.append(checkpoint)
        print(f"Modelo offline verificado: {model_id} ({spec.size_label})")
    return tuple(checkpoints)


def build(*, prepare_only: bool = False) -> Path:
    """Compila o aplicativo como diretório, sem extração gigante a cada abertura."""
    root = Path(__file__).resolve().parent
    platform_key = FFmpegFinder.platform_key()
    ffmpeg = FFmpegFinder.ensure_static(progress=lambda value: print(f"FFmpeg: {value}%"))
    print(f"FFmpeg verificado: {ffmpeg}")
    if prepare_only:
        return ffmpeg
    bundled_models = prepare_bundled_models()

    separator = os.pathsep
    icon = root / "assets" / ("icon.ico" if platform_key == "windows" else "icon.png")
    if not icon.is_file():
        raise FileNotFoundError(f"Ícone obrigatório não encontrado: {icon}")
    manifest_args: list[str] = []
    if platform_key == "windows":
        executable_manifest = (
            root / "packaging" / "windows" / "WhisperTranscriber.exe.manifest"
        )
        if not executable_manifest.is_file():
            raise FileNotFoundError(
                f"Manifesto do executável não encontrado: {executable_manifest}"
            )
        manifest_args = ["--manifest", str(executable_manifest)]

    model_data_args = [
        argument
        for checkpoint in bundled_models
        for argument in (
            "--add-data",
            f"{checkpoint}{separator}assets/models",
        )
    ]
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onedir",
        "--windowed",
        "--name",
        APP_EXECUTABLE,
        "--icon",
        str(icon),
        *manifest_args,
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
        *model_data_args,
        str(root / "main.py"),
    ]
    print("Iniciando compilação do diretório instalável...")
    subprocess.run(command, cwd=root, check=True)
    suffix = ".exe" if platform_key == "windows" else ""
    executable = root / "dist" / APP_EXECUTABLE / f"{APP_EXECUTABLE}{suffix}"
    if not executable.is_file():
        raise RuntimeError("O PyInstaller terminou sem gerar o executável esperado.")
    shutil.copy2(_license_file(), executable.parent / "LICENSE")
    shutil.copy2(_third_party_notice(), executable.parent / "THIRD_PARTY_NOTICES.md")
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
    models = payload.get("modelos_offline", {})
    if not isinstance(models, dict) or any(
        models.get(model_id) != "bundled" for model_id in BUNDLED_MODEL_IDS
    ):
        raise RuntimeError(f"O build não contém todos os modelos offline: {models}")
    print(f"Executável verificado: {device}")
    if runtime:
        print(f"Runtime incorporado: {runtime}")
    return payload


def build_portable_archive(executable: Path) -> Path:
    """Arquiva o diretório instalável sem reextrair modelos a cada abertura."""

    if not executable.is_file() or executable.parent.name != APP_EXECUTABLE:
        raise ValueError("O portátil exige o build PyInstaller no modo --onedir.")
    root = Path(__file__).resolve().parent
    if sys.platform.startswith("win"):
        destination = root / "dist" / WINDOWS_PORTABLE_NAME
        destination.unlink(missing_ok=True)
        with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_STORED) as zipped:
            for path in executable.parent.rglob("*"):
                if path.is_file():
                    zipped.write(path, path.relative_to(executable.parent.parent))
        archive = str(destination)
    else:
        destination = root / "dist" / LINUX_PORTABLE_NAME
        destination.unlink(missing_ok=True)
        with tarfile.open(destination, "w:gz", compresslevel=1) as packed:
            packed.add(executable.parent, arcname=executable.parent.name)
        archive = str(destination)
    result = Path(archive).resolve()
    if not result.is_file():
        raise RuntimeError("A geração do pacote portátil não produziu o arquivo esperado.")
    print(f"Pacote portátil concluído: {result}")
    return result


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


def _license_file() -> Path:
    license_file = Path(__file__).resolve().parent / "LICENSE"
    if license_file.is_file():
        return license_file
    raise FileNotFoundError("LICENSE não foi encontrado.")


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
        shutil.copy2(_license_file(), stage / "LICENSE")
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


def build_installer(
    executable: Path, *, output_name: str = INSTALLER_NAME
) -> Path:
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
    if Path(output_name).name != output_name or not output_name.lower().endswith(".exe"):
        raise ValueError("O nome de saída do instalador deve ser um arquivo .exe simples.")
    output_dir = root / "dist" / "installer"
    output_dir.mkdir(parents=True, exist_ok=True)
    installer = output_dir / output_name
    installer.unlink(missing_ok=True)
    for stale_slice in installer_slices(installer):
        stale_slice.unlink()
    command = [
        str(find_iscc()),
        "/Qp",
        f"/O{output_dir}",
        f"/DAppVersion={__version__}",
        f"/DOutputBaseFilename={installer.stem}",
        f"/DSourceDir={source_dir}",
        f"/DRootDir={root}",
        str(script),
    ]
    print("Compilando o instalador Windows...")
    subprocess.run(command, cwd=root, check=True)
    if not installer.is_file():
        raise RuntimeError("O Inno Setup terminou sem gerar o instalador esperado.")
    slices = installer_slices(installer)
    if not slices:
        raise RuntimeError("O Inno Setup não gerou as fatias offline obrigatórias.")
    print(f"Instalador concluído: {installer}")
    print(f"Fatias offline: {len(slices)}")
    return installer


def installer_slices(installer: Path) -> list[Path]:
    """Lista somente as fatias numeradas pertencentes ao launcher informado."""

    pattern = re.compile(rf"{re.escape(installer.stem)}-\d+\.bin", re.IGNORECASE)
    return sorted(
        path
        for path in installer.parent.iterdir()
        if path.is_file() and pattern.fullmatch(path.name)
    )


def build_installer_bundle(installer: Path) -> Path:
    """Agrupa launcher e fatias Inno em um ZIP indivisível para distribuição."""

    slices = installer_slices(installer)
    if not installer.is_file() or not slices:
        raise FileNotFoundError("Launcher ou fatias do instalador offline não encontrados.")
    bundle_name = (
        CPU_INSTALLER_BUNDLE_NAME
        if installer.name == CPU_INSTALLER_NAME
        else CUDA_INSTALLER_BUNDLE_NAME
    )
    destination = installer.parent / bundle_name
    destination.unlink(missing_ok=True)
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_STORED) as archive:
        for payload in (installer, *slices):
            archive.write(payload, payload.name)
    print(f"Bundle completo do instalador: {destination}")
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description="Compila o Whisper Transcriber Desktop")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--prepare-ffmpeg",
        action="store_true",
        help="baixa e verifica o FFmpeg sem executar o PyInstaller",
    )
    mode.add_argument(
        "--prepare-models",
        action="store_true",
        help="baixa e verifica os checkpoints incorporados sem compilar",
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
    if args.prepare_models:
        prepare_bundled_models()
        return 0
    if args.installer_only:
        executable = (
            Path(__file__).resolve().parent
            / "dist"
            / APP_EXECUTABLE
            / f"{APP_EXECUTABLE}.exe"
        )
        installer = build_installer(executable)
        build_installer_bundle(installer)
        return 0
    if args.installer:
        executable = build()
        verify_executable(
            executable,
            require_runtime="NVIDIA CUDA",
            allow_policy_block=True,
        )
        installer = build_installer(executable)
        build_installer_bundle(installer)
        return 0
    if args.installer_cpu:
        executable = build()
        verify_executable(
            executable,
            require_runtime="CPU",
            allow_policy_block=True,
        )
        installer = build_installer(executable, output_name=CPU_INSTALLER_NAME)
        build_installer_bundle(installer)
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
        executable = build()
        verify_executable(
            executable,
            require_cuda=True,
            require_runtime="NVIDIA CUDA",
            allow_policy_block=True,
        )
        package = build_msix(executable)
        verify_msix(package)
        return 0
    executable = build()
    verify_executable(executable)
    build_portable_archive(executable)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
