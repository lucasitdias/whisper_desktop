"""Resolução e provisionamento seguro do executável FFmpeg."""

from __future__ import annotations

import hashlib
import os
import platform
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path


class FFmpegError(RuntimeError):
    """Erro relacionado à disponibilidade do FFmpeg."""


@dataclass(frozen=True, slots=True)
class FFmpegAsset:
    url: str
    sha256: str
    archive_type: str
    binary_name: str


_RELEASE_BASE = (
    "https://github.com/BtbN/FFmpeg-Builds/releases/download/"
    "autobuild-2026-07-31-14-10"
)
FFMPEG_ASSETS: dict[str, FFmpegAsset] = {
    "windows": FFmpegAsset(
        url=f"{_RELEASE_BASE}/ffmpeg-n8.1.2-34-g9b6c8969e0-win64-lgpl-8.1.zip",
        sha256="089e4169e93b2b3f3acbfced3c0704d24276a225641bdda04d796d28b07a2a38",
        archive_type="zip",
        binary_name="ffmpeg.exe",
    ),
    "linux": FFmpegAsset(
        url=f"{_RELEASE_BASE}/ffmpeg-n8.1.2-34-g9b6c8969e0-linux64-lgpl-8.1.tar.xz",
        sha256="8c8b2897f2a8093ae2d985f7f1867d218451d4c567c1b2437f86a7c73a950b9f",
        archive_type="tar.xz",
        binary_name="ffmpeg",
    ),
}


class FFmpegFinder:
    """Localiza o FFmpeg empacotado, do projeto, do PATH ou do cache local."""

    VERSION = "8.1.2-34-g9b6c8969e0"
    MAX_ARCHIVE_BYTES = 1024 * 1024 * 1024

    @classmethod
    def platform_key(cls) -> str:
        machine = platform.machine().lower()
        if machine not in {"amd64", "x86_64"}:
            raise FFmpegError(
                f"Arquitetura não suportada: {machine or 'desconhecida'}. "
                "Use Windows ou Linux x86_64."
            )
        if sys.platform.startswith("win"):
            return "windows"
        if sys.platform.startswith("linux"):
            return "linux"
        raise FFmpegError("Sistema não suportado. Use Windows 10/11 ou Linux x86_64.")

    @classmethod
    def project_root(cls) -> Path:
        return Path(__file__).resolve().parents[2]

    @classmethod
    def resource_root(cls) -> Path:
        bundle_root = getattr(sys, "_MEIPASS", None)
        return Path(bundle_root) if bundle_root else cls.project_root()

    @classmethod
    def cache_root(cls) -> Path:
        if sys.platform.startswith("win"):
            base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        else:
            base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
        return base / "WhisperTranscriber" / "ffmpeg" / cls.VERSION

    @classmethod
    def asset(cls) -> FFmpegAsset:
        return FFMPEG_ASSETS[cls.platform_key()]

    @classmethod
    def bundled_path(cls) -> Path:
        key = cls.platform_key()
        return cls.resource_root() / "assets" / "ffmpeg" / key / cls.asset().binary_name

    @classmethod
    def cache_path(cls) -> Path:
        return cls.cache_root() / cls.platform_key() / cls.asset().binary_name

    @classmethod
    def resolve(cls, *, download_if_missing: bool = False) -> Path:
        candidates = [cls.bundled_path()]
        project_asset = (
            cls.project_root()
            / "assets"
            / "ffmpeg"
            / cls.platform_key()
            / cls.asset().binary_name
        )
        if project_asset not in candidates:
            candidates.append(project_asset)
        for candidate in candidates:
            if candidate.is_file() and cls.validate(candidate):
                return candidate.resolve()

        from_path = shutil.which("ffmpeg")
        if from_path and cls.validate(Path(from_path)):
            return Path(from_path).resolve()
        cached = cls.cache_path()
        if cached.is_file() and cls.validate(cached):
            return cached.resolve()
        if download_if_missing:
            return cls.download()
        raise FFmpegError(
            "FFmpeg não encontrado nos recursos do aplicativo, no projeto, no PATH ou no cache."
        )

    @classmethod
    def ensure_available(cls, progress: Callable[[int], None] | None = None) -> Path:
        try:
            return cls.resolve()
        except FFmpegError as error:
            if "não encontrado" not in str(error):
                raise
        return cls.download(progress=progress)

    @classmethod
    def ensure_static(cls, progress: Callable[[int], None] | None = None) -> Path:
        """Obtém exclusivamente a compilação estática fixada usada nos builds."""
        cached = cls.cache_path()
        if cached.is_file() and cls.validate(cached):
            return cached.resolve()
        return cls.download(progress=progress)

    @staticmethod
    def validate(binary: Path) -> bool:
        try:
            result = subprocess.run(
                [str(binary), "-version"],
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=(
                    subprocess.CREATE_NO_WINDOW if sys.platform.startswith("win") else 0
                ),
            )
        except (OSError, subprocess.SubprocessError):
            return False
        first_line = (result.stdout or result.stderr).splitlines()
        return (
            result.returncode == 0
            and bool(first_line)
            and "ffmpeg version" in first_line[0].lower()
        )

    @classmethod
    def prepend_to_path(cls, binary: Path) -> None:
        parent = str(binary.resolve().parent)
        entries = os.environ.get("PATH", "").split(os.pathsep)
        if parent not in entries:
            os.environ["PATH"] = os.pathsep.join([parent, *entries])

    @classmethod
    def download(cls, progress: Callable[[int], None] | None = None) -> Path:
        asset = cls.asset()
        destination = cls.cache_path()
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="whisper-ffmpeg-") as temp_dir:
            archive = Path(temp_dir) / Path(asset.url).name
            request = urllib.request.Request(
                asset.url, headers={"User-Agent": "WhisperTranscriber/0.1"}
            )
            digest = hashlib.sha256()
            with (
                urllib.request.urlopen(request, timeout=60) as response,
                archive.open("wb") as output,
            ):
                total = int(response.headers.get("Content-Length", "0"))
                if total > cls.MAX_ARCHIVE_BYTES:
                    raise FFmpegError("O arquivo informado para o FFmpeg excede o limite seguro.")
                downloaded = 0
                while chunk := response.read(1024 * 1024):
                    if downloaded + len(chunk) > cls.MAX_ARCHIVE_BYTES:
                        raise FFmpegError(
                            "O download do FFmpeg excedeu o limite seguro."
                        )
                    output.write(chunk)
                    digest.update(chunk)
                    downloaded += len(chunk)
                    if progress and total:
                        progress(min(100, int(downloaded * 100 / total)))
            if digest.hexdigest().lower() != asset.sha256:
                raise FFmpegError(
                    "Falha de segurança: o checksum SHA-256 do FFmpeg não corresponde ao esperado."
                )
            temporary_binary = destination.with_suffix(destination.suffix + ".tmp")
            cls._extract_binary(archive, temporary_binary, asset)
            if not sys.platform.startswith("win"):
                temporary_binary.chmod(
                    temporary_binary.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
                )
            os.replace(temporary_binary, destination)
        if not cls.validate(destination):
            destination.unlink(missing_ok=True)
            raise FFmpegError("O FFmpeg baixado não pôde ser executado.")
        return destination.resolve()

    @staticmethod
    def _extract_binary(archive: Path, destination: Path, asset: FFmpegAsset) -> None:
        if asset.archive_type == "zip":
            with zipfile.ZipFile(archive) as package:
                members = [
                    name
                    for name in package.namelist()
                    if name.replace("\\", "/").endswith(f"/bin/{asset.binary_name}")
                ]
                if len(members) != 1:
                    raise FFmpegError("Estrutura inesperada no arquivo ZIP do FFmpeg.")
                with package.open(members[0]) as source, destination.open("wb") as output:
                    shutil.copyfileobj(source, output)
            return
        if asset.archive_type == "tar.xz":
            with tarfile.open(archive, mode="r:xz") as package:
                members = [
                    member
                    for member in package.getmembers()
                    if member.isfile()
                    and member.name.replace("\\", "/").endswith(f"/bin/{asset.binary_name}")
                ]
                if len(members) != 1:
                    raise FFmpegError("Estrutura inesperada no arquivo TAR do FFmpeg.")
                source = package.extractfile(members[0])
                if source is None:
                    raise FFmpegError("Não foi possível extrair o FFmpeg.")
                with source, destination.open("wb") as output:
                    shutil.copyfileobj(source, output)
            return
        raise FFmpegError(f"Formato de arquivo não suportado: {asset.archive_type}.")
