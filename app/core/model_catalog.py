"""Catálogo e armazenamento seguro dos modelos Whisper suportados."""

from __future__ import annotations

import hashlib
import os
import shutil
import sys
import threading
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from PySide6.QtCore import QThread, Signal


class ModelAvailability(StrEnum):
    BUNDLED = "bundled"
    CACHED = "cached"
    DOWNLOAD_REQUIRED = "download_required"
    DOWNLOADING = "downloading"
    INVALID = "invalid"


@dataclass(frozen=True, slots=True)
class ModelSpec:
    model_id: str
    filename: str
    url: str
    sha256: str
    size_bytes: int
    parameters: int
    required_vram: str
    relative_speed: str
    fidelity: str
    bundled: bool
    beam_size: int = 5

    @property
    def size_label(self) -> str:
        gib = self.size_bytes / (1024**3)
        return f"{gib:.1f} GB" if gib >= 1 else f"{self.size_bytes / (1024**2):.0f} MB"

    @property
    def parameters_label(self) -> str:
        return f"{self.parameters / 1_000_000:,.0f}M".replace(",", ".")

    @property
    def availability_prefix(self) -> str:
        return "Offline" if self.bundled else "Requer download"

    @property
    def display_label(self) -> str:
        return f"{self.availability_prefix} — {self.model_id} — {self.fidelity}"

    @property
    def tooltip(self) -> str:
        network = (
            "Incluído no instalador e disponível sem internet."
            if self.bundled
            else "Exige um download explícito; depois funciona totalmente offline."
        )
        return (
            f"{self.model_id}: {self.parameters_label} parâmetros, VRAM aproximada "
            f"{self.required_vram}, velocidade relativa {self.relative_speed}, "
            f"checkpoint {self.size_label}. {network}"
        )


def _spec(
    model_id: str,
    filename: str,
    sha256: str,
    size_bytes: int,
    parameters: int,
    required_vram: str,
    relative_speed: str,
    fidelity: str,
    *,
    bundled: bool,
    beam_size: int = 5,
) -> ModelSpec:
    return ModelSpec(
        model_id=model_id,
        filename=filename,
        url=(
            "https://openaipublic.azureedge.net/main/whisper/models/"
            f"{sha256}/{filename}"
        ),
        sha256=sha256,
        size_bytes=size_bytes,
        parameters=parameters,
        required_vram=required_vram,
        relative_speed=relative_speed,
        fidelity=fidelity,
        bundled=bundled,
        beam_size=beam_size,
    )


MODEL_SPECS = (
    _spec(
        "medium",
        "medium.pt",
        "345ae4da62f9b3d59415adc60127b97c714f32e89e936602e85993674d08dcb1",
        1_528_008_539,
        769_000_000,
        "~5 GB",
        "~2x",
        "alta precisão equilibrada",
        bundled=True,
    ),
    _spec(
        "turbo",
        "large-v3-turbo.pt",
        "aff26ae408abcba5fbf8813c21e62b0941638c5f6eebfb145be0c9839262a19a",
        1_617_941_637,
        809_000_000,
        "~6 GB",
        "~8x",
        "rápido e preciso",
        bundled=True,
        beam_size=3,
    ),
    _spec(
        "large-v3",
        "large-v3.pt",
        "e5b1a55b89c1367dacf97e3e19bfd829a01529dbfdeefa8caeb59b3f1b81dadb",
        3_087_371_615,
        1_550_000_000,
        "~10 GB",
        "1x",
        "máxima fidelidade",
        bundled=False,
    ),
    _spec(
        "tiny",
        "tiny.pt",
        "65147644a518d12f04e32d6f3b26facc3f8dd46e5390956a9424a650c0ce22b9",
        75_572_083,
        39_000_000,
        "~1 GB",
        "~10x",
        "máxima velocidade",
        bundled=False,
    ),
    _spec(
        "base",
        "base.pt",
        "ed3a0b6b1c0edf879ad9b11b1af5a0e6ab5db9205f891f668f8b0e6c6326e34e",
        145_262_807,
        74_000_000,
        "~1 GB",
        "~7x",
        "rápido",
        bundled=False,
    ),
    _spec(
        "small",
        "small.pt",
        "9ecf779972d90ba49c06d968637d720dd632c55bbf19d441fb42bf17a411e794",
        483_617_219,
        244_000_000,
        "~2 GB",
        "~4x",
        "equilíbrio para hardware modesto",
        bundled=False,
    ),
)
MODEL_BY_ID = {spec.model_id: spec for spec in MODEL_SPECS}
BUNDLED_MODEL_IDS = tuple(spec.model_id for spec in MODEL_SPECS if spec.bundled)


class ModelUnavailableError(RuntimeError):
    """O checkpoint escolhido ainda não está disponível localmente."""


class ModelIntegrityError(RuntimeError):
    """O checkpoint não corresponde ao artefato oficial fixado."""


class ModelDownloadCancelled(RuntimeError):
    """Download interrompido cooperativamente."""


class ModelManager:
    """Resolve checkpoints incorporados/cacheados sem baixar durante a transcrição."""

    _verified: set[tuple[str, int, int]] = set()
    _verification_lock = threading.RLock()

    @staticmethod
    def bundled_root() -> Path:
        if hasattr(sys, "_MEIPASS"):
            return Path(sys._MEIPASS) / "assets" / "models"
        return Path(__file__).resolve().parents[2] / "assets" / "models"

    @staticmethod
    def cache_root() -> Path:
        if sys.platform.startswith("win"):
            base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        else:
            base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
        return base / "WhisperTranscriber" / "models"

    @classmethod
    def candidates(cls, spec: ModelSpec) -> tuple[tuple[ModelAvailability, Path], ...]:
        return (
            (ModelAvailability.BUNDLED, cls.bundled_root() / spec.filename),
            (ModelAvailability.CACHED, cls.cache_root() / spec.filename),
        )

    @classmethod
    def availability(cls, spec: ModelSpec) -> ModelAvailability:
        invalid_found = False
        for availability, path in cls.candidates(spec):
            if not path.exists():
                continue
            if path.is_file() and path.stat().st_size == spec.size_bytes:
                return availability
            invalid_found = True
        return ModelAvailability.INVALID if invalid_found else ModelAvailability.DOWNLOAD_REQUIRED

    @classmethod
    def resolve(cls, spec: ModelSpec) -> Path | None:
        for _availability, path in cls.candidates(spec):
            if path.is_file() and path.stat().st_size == spec.size_bytes:
                return path.resolve()
        return None

    @classmethod
    def require_checkpoint(
        cls,
        spec: ModelSpec,
        *,
        progress: Callable[[int], None] | None = None,
        cancelled: Callable[[], bool] | None = None,
    ) -> Path:
        checkpoint = cls.resolve(spec)
        if checkpoint is None:
            raise ModelUnavailableError(
                f"O modelo {spec.model_id} não está disponível neste computador. "
                "Escolha um modelo Offline ou use Baixar modelo quando houver internet."
            )
        cls.verify(checkpoint, spec, progress=progress, cancelled=cancelled)
        return checkpoint

    @classmethod
    def verify(
        cls,
        checkpoint: Path,
        spec: ModelSpec,
        *,
        progress: Callable[[int], None] | None = None,
        cancelled: Callable[[], bool] | None = None,
    ) -> None:
        stat = checkpoint.stat()
        cache_key = (str(checkpoint), stat.st_size, stat.st_mtime_ns)
        with cls._verification_lock:
            if cache_key in cls._verified:
                return
        if stat.st_size != spec.size_bytes:
            raise ModelIntegrityError(f"O arquivo do modelo {spec.model_id} está incompleto.")
        digest = hashlib.sha256()
        processed = 0
        with checkpoint.open("rb") as stream:
            while block := stream.read(4 * 1024 * 1024):
                if cancelled and cancelled():
                    raise ModelDownloadCancelled
                digest.update(block)
                processed += len(block)
                if progress:
                    progress(min(100, round(processed / spec.size_bytes * 100)))
        if digest.hexdigest() != spec.sha256:
            raise ModelIntegrityError(
                f"A verificação de integridade do modelo {spec.model_id} falhou."
            )
        with cls._verification_lock:
            cls._verified.add(cache_key)


def download_checkpoint(
    spec: ModelSpec,
    *,
    destination_root: Path | None = None,
    progress: Callable[[int], None] | None = None,
    status: Callable[[str], None] | None = None,
    cancelled: Callable[[], bool] | None = None,
) -> Path:
    """Baixa, valida e publica um checkpoint oficial de forma atômica."""

    root = destination_root or ModelManager.cache_root()
    target = root / spec.filename
    partial = target.with_suffix(target.suffix + ".part")
    root.mkdir(parents=True, exist_ok=True)
    if target.is_file() and target.stat().st_size == spec.size_bytes:
        ModelManager.verify(target, spec, progress=progress, cancelled=cancelled)
        return target.resolve()
    free = shutil.disk_usage(root).free
    if free < spec.size_bytes + 128 * 1024 * 1024:
        raise OSError(
            f"Espaço insuficiente para baixar {spec.model_id} ({spec.size_label})."
        )
    partial.unlink(missing_ok=True)
    if status:
        status(f"Baixando {spec.model_id} ({spec.size_label})...")
    request = urllib.request.Request(
        spec.url,
        headers={"User-Agent": "WhisperTranscriberDesktop/0.3.0"},
    )
    digest = hashlib.sha256()
    downloaded = 0
    try:
        with urllib.request.urlopen(request, timeout=60) as source, partial.open("wb") as out:
            while block := source.read(1024 * 1024):
                if cancelled and cancelled():
                    raise ModelDownloadCancelled
                if downloaded + len(block) > spec.size_bytes:
                    raise ModelIntegrityError(
                        f"O download de {spec.model_id} excede o tamanho oficial."
                    )
                out.write(block)
                digest.update(block)
                downloaded += len(block)
                if progress:
                    progress(min(99, round(downloaded / spec.size_bytes * 100)))
            out.flush()
            os.fsync(out.fileno())
        if downloaded != spec.size_bytes or digest.hexdigest() != spec.sha256:
            raise ModelIntegrityError(
                f"O download de {spec.model_id} não corresponde ao arquivo oficial."
            )
        os.replace(partial, target)
        if progress:
            progress(100)
        return target.resolve()
    except Exception:
        partial.unlink(missing_ok=True)
        raise


class ModelDownloadWorker(QThread):
    """Baixa um checkpoint opcional com progresso, checksum e troca atômica."""

    progress_changed = Signal(int)
    status_changed = Signal(str)
    completed = Signal(object)
    failed = Signal(str)
    cancelled = Signal(str)

    def __init__(self, spec: ModelSpec, parent: object = None) -> None:
        super().__init__(parent)
        self.spec = spec
        self._cancel_event = threading.Event()

    def cancel(self) -> None:
        self._cancel_event.set()
        self.requestInterruption()

    def _is_cancelled(self) -> bool:
        return self._cancel_event.is_set() or self.isInterruptionRequested()

    def run(self) -> None:
        try:
            target = download_checkpoint(
                self.spec,
                progress=self.progress_changed.emit,
                status=self.status_changed.emit,
                cancelled=self._is_cancelled,
            )
            self.completed.emit(target)
        except ModelDownloadCancelled:
            self.cancelled.emit("Download cancelado; nenhum arquivo parcial foi mantido.")
        except (OSError, urllib.error.URLError, ModelIntegrityError) as error:
            self.failed.emit(f"Não foi possível baixar {self.spec.model_id}: {error}")
