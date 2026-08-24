import hashlib
import io
import zipfile
from pathlib import Path

import pytest

from app.core.ffmpeg_finder import FFmpegAsset, FFmpegError, FFmpegFinder


def test_resolve_prioriza_binario_empacotado(monkeypatch, tmp_path: Path):
    binary = tmp_path / "assets" / "ffmpeg" / "windows" / "ffmpeg.exe"
    binary.parent.mkdir(parents=True)
    binary.write_bytes(b"fake")
    monkeypatch.setattr(FFmpegFinder, "platform_key", classmethod(lambda cls: "windows"))
    monkeypatch.setattr(FFmpegFinder, "resource_root", classmethod(lambda cls: tmp_path))
    monkeypatch.setattr(FFmpegFinder, "project_root", classmethod(lambda cls: tmp_path))
    monkeypatch.setattr(FFmpegFinder, "validate", staticmethod(lambda path: path == binary))
    assert FFmpegFinder.resolve() == binary.resolve()


def test_resolve_faz_fallback_para_path(monkeypatch, tmp_path: Path):
    binary = tmp_path / "ffmpeg.exe"
    binary.write_bytes(b"fake")
    monkeypatch.setattr(FFmpegFinder, "platform_key", classmethod(lambda cls: "windows"))
    monkeypatch.setattr(FFmpegFinder, "resource_root", classmethod(lambda cls: tmp_path / "bundle"))
    monkeypatch.setattr(FFmpegFinder, "project_root", classmethod(lambda cls: tmp_path / "project"))
    monkeypatch.setattr("app.core.ffmpeg_finder.shutil.which", lambda name: str(binary))
    monkeypatch.setattr(FFmpegFinder, "validate", staticmethod(lambda path: Path(path) == binary))
    assert FFmpegFinder.resolve() == binary.resolve()


def test_extrai_somente_binario_esperado(tmp_path: Path):
    archive = tmp_path / "ffmpeg.zip"
    with zipfile.ZipFile(archive, "w") as package:
        package.writestr("ffmpeg/bin/ffmpeg.exe", b"binary")
        package.writestr("../../fora.txt", b"unsafe")
    destination = tmp_path / "ffmpeg.exe"
    asset = FFmpegAsset("https://example.invalid/a.zip", "", "zip", "ffmpeg.exe")
    FFmpegFinder._extract_binary(archive, destination, asset)
    assert destination.read_bytes() == b"binary"
    assert not (tmp_path.parent / "fora.txt").exists()


class FakeResponse(io.BytesIO):
    def __init__(self, data: bytes):
        super().__init__(data)
        self.headers = {"Content-Length": str(len(data))}

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()


def test_download_rejeita_checksum_incorreto(monkeypatch, tmp_path: Path):
    payload = b"arquivo adulterado"
    asset = FFmpegAsset("https://example.invalid/a.zip", "0" * 64, "zip", "ffmpeg.exe")
    monkeypatch.setattr(FFmpegFinder, "asset", classmethod(lambda cls: asset))
    monkeypatch.setattr(
        FFmpegFinder,
        "cache_path",
        classmethod(lambda cls: tmp_path / "ffmpeg.exe"),
    )
    monkeypatch.setattr(
        "app.core.ffmpeg_finder.urllib.request.urlopen",
        lambda *_args, **_kwargs: FakeResponse(payload),
    )
    with pytest.raises(FFmpegError, match="checksum"):
        FFmpegFinder.download()
    assert hashlib.sha256(payload).hexdigest() != asset.sha256


def test_download_rejeita_arquivo_acima_do_limite(monkeypatch, tmp_path: Path):
    asset = FFmpegAsset("https://example.invalid/a.zip", "0" * 64, "zip", "ffmpeg.exe")
    response = FakeResponse(b"")
    response.headers["Content-Length"] = str(FFmpegFinder.MAX_ARCHIVE_BYTES + 1)
    monkeypatch.setattr(FFmpegFinder, "asset", classmethod(lambda cls: asset))
    monkeypatch.setattr(
        FFmpegFinder,
        "cache_path",
        classmethod(lambda cls: tmp_path / "ffmpeg.exe"),
    )
    monkeypatch.setattr(
        "app.core.ffmpeg_finder.urllib.request.urlopen",
        lambda *_args, **_kwargs: response,
    )

    with pytest.raises(FFmpegError, match="limite seguro"):
        FFmpegFinder.download()


def test_ensure_static_usa_cache_validado(monkeypatch, tmp_path: Path):
    cached = tmp_path / "ffmpeg.exe"
    cached.write_bytes(b"binary")
    monkeypatch.setattr(FFmpegFinder, "cache_path", classmethod(lambda cls: cached))
    monkeypatch.setattr(FFmpegFinder, "validate", staticmethod(lambda path: path == cached))
    monkeypatch.setattr(
        FFmpegFinder,
        "download",
        classmethod(lambda cls, progress=None: pytest.fail("download inesperado")),
    )

    assert FFmpegFinder.ensure_static() == cached.resolve()


def test_platforma_nao_suportada(monkeypatch):
    monkeypatch.setattr("app.core.ffmpeg_finder.platform.machine", lambda: "arm64")

    with pytest.raises(FFmpegError, match="Arquitetura não suportada"):
        FFmpegFinder.platform_key()
