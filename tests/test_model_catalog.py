import hashlib
import io
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.core.model_catalog import (
    BUNDLED_MODEL_IDS,
    MODEL_BY_ID,
    MODEL_SPECS,
    ModelAvailability,
    ModelDownloadCancelled,
    ModelIntegrityError,
    ModelManager,
    ModelSpec,
    ModelUnavailableError,
    download_checkpoint,
)


def _small_spec(payload: bytes, *, bundled: bool = False) -> ModelSpec:
    return ModelSpec(
        model_id="teste",
        filename="teste.pt",
        url="https://example.invalid/teste.pt",
        sha256=hashlib.sha256(payload).hexdigest(),
        size_bytes=len(payload),
        parameters=1_000_000,
        required_vram="~1 GB",
        relative_speed="~10x",
        fidelity="teste",
        bundled=bundled,
    )


@pytest.fixture(autouse=True)
def limpa_cache_de_verificacao():
    ModelManager._verified.clear()
    yield
    ModelManager._verified.clear()


def test_catalogo_multilingue_tem_seis_modelos_sem_alias_ou_en():
    assert [spec.model_id for spec in MODEL_SPECS] == [
        "medium",
        "turbo",
        "large-v3",
        "tiny",
        "base",
        "small",
    ]
    assert BUNDLED_MODEL_IDS == ("medium", "turbo")
    assert all(not spec.model_id.endswith(".en") for spec in MODEL_SPECS)
    assert "large" not in MODEL_BY_ID


def test_catalogo_expoe_parametros_vram_velocidade_e_disponibilidade():
    large = MODEL_BY_ID["large-v3"]
    turbo = MODEL_BY_ID["turbo"]
    assert large.parameters_label == "1.550M"
    assert large.required_vram == "~10 GB"
    assert large.relative_speed == "1x"
    assert large.display_label == "Requer download — large-v3 — máxima fidelidade"
    assert turbo.filename == "large-v3-turbo.pt"
    assert "809M" in turbo.tooltip
    assert "download explícito" in large.tooltip
    assert "download explícito" in MODEL_BY_ID["small"].tooltip


def test_disponibilidade_prioriza_incorporado_e_depois_cache(
    monkeypatch, tmp_path: Path
):
    payload = b"checkpoint"
    spec = _small_spec(payload, bundled=True)
    bundled = tmp_path / "bundle"
    cached = tmp_path / "cache"
    monkeypatch.setattr(ModelManager, "bundled_root", staticmethod(lambda: bundled))
    monkeypatch.setattr(ModelManager, "cache_root", staticmethod(lambda: cached))

    assert ModelManager.availability(spec) is ModelAvailability.DOWNLOAD_REQUIRED
    cached.mkdir()
    (cached / spec.filename).write_bytes(payload)
    assert ModelManager.availability(spec) is ModelAvailability.CACHED
    bundled.mkdir()
    (bundled / spec.filename).write_bytes(payload)
    assert ModelManager.availability(spec) is ModelAvailability.BUNDLED


def test_arquivo_incompleto_e_marcado_como_invalido(monkeypatch, tmp_path: Path):
    spec = _small_spec(b"correto")
    monkeypatch.setattr(ModelManager, "bundled_root", staticmethod(lambda: tmp_path / "b"))
    monkeypatch.setattr(ModelManager, "cache_root", staticmethod(lambda: tmp_path / "c"))
    (tmp_path / "c").mkdir()
    (tmp_path / "c" / spec.filename).write_bytes(b"x")
    assert ModelManager.availability(spec) is ModelAvailability.INVALID
    with pytest.raises(ModelUnavailableError):
        ModelManager.require_checkpoint(spec)


def test_verificacao_rejeita_checksum_incorreto(tmp_path: Path):
    spec = _small_spec(b"esperado")
    checkpoint = tmp_path / spec.filename
    checkpoint.write_bytes(b"alterado")
    spec_mesmo_tamanho = replace(spec, size_bytes=len(b"alterado"))
    with pytest.raises(ModelIntegrityError, match="integridade"):
        ModelManager.verify(checkpoint, spec_mesmo_tamanho)


def test_download_publica_atomicamente_e_remove_part(monkeypatch, tmp_path: Path):
    payload = b"modelo oficial"
    spec = _small_spec(payload)
    monkeypatch.setattr(
        "app.core.model_catalog.urllib.request.urlopen",
        lambda *_args, **_kwargs: io.BytesIO(payload),
    )
    monkeypatch.setattr(
        "app.core.model_catalog.shutil.disk_usage",
        lambda _path: SimpleNamespace(free=10**9),
    )
    progress: list[int] = []

    result = download_checkpoint(spec, destination_root=tmp_path, progress=progress.append)

    assert result.read_bytes() == payload
    assert progress[-1] == 100
    assert not (tmp_path / "teste.pt.part").exists()


def test_download_cancelado_nao_mantem_arquivo_parcial(monkeypatch, tmp_path: Path):
    payload = b"modelo oficial"
    spec = _small_spec(payload)
    monkeypatch.setattr(
        "app.core.model_catalog.urllib.request.urlopen",
        lambda *_args, **_kwargs: io.BytesIO(payload),
    )
    monkeypatch.setattr(
        "app.core.model_catalog.shutil.disk_usage",
        lambda _path: SimpleNamespace(free=10**9),
    )

    with pytest.raises(ModelDownloadCancelled):
        download_checkpoint(spec, destination_root=tmp_path, cancelled=lambda: True)

    assert not (tmp_path / spec.filename).exists()
    assert not (tmp_path / "teste.pt.part").exists()


def test_download_rejeita_checksum_e_espaco_insuficiente(monkeypatch, tmp_path: Path):
    spec = _small_spec(b"modelo correto")
    monkeypatch.setattr(
        "app.core.model_catalog.urllib.request.urlopen",
        lambda *_args, **_kwargs: io.BytesIO(b"modelo errado!"),
    )
    monkeypatch.setattr(
        "app.core.model_catalog.shutil.disk_usage",
        lambda _path: SimpleNamespace(free=10**9),
    )
    with pytest.raises(ModelIntegrityError):
        download_checkpoint(spec, destination_root=tmp_path)

    monkeypatch.setattr(
        "app.core.model_catalog.shutil.disk_usage",
        lambda _path: SimpleNamespace(free=0),
    )
    with pytest.raises(OSError, match="Espaço insuficiente"):
        download_checkpoint(spec, destination_root=tmp_path)


def test_download_interrompe_resposta_maior_que_o_checkpoint(monkeypatch, tmp_path: Path):
    spec = _small_spec(b"modelo")
    monkeypatch.setattr(
        "app.core.model_catalog.urllib.request.urlopen",
        lambda *_args, **_kwargs: io.BytesIO(b"modelo com conteudo excedente"),
    )
    monkeypatch.setattr(
        "app.core.model_catalog.shutil.disk_usage",
        lambda _path: SimpleNamespace(free=10**9),
    )

    with pytest.raises(ModelIntegrityError, match="excede o tamanho oficial"):
        download_checkpoint(spec, destination_root=tmp_path)

    assert not (tmp_path / spec.filename).exists()
    assert not (tmp_path / "teste.pt.part").exists()
