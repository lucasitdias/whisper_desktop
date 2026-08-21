import json
import zipfile
from pathlib import Path

import pytest

import build


def test_find_iscc_usa_caminho_configurado(monkeypatch, tmp_path: Path):
    compiler = tmp_path / "ISCC.exe"
    compiler.write_bytes(b"compiler")
    monkeypatch.setenv("ISCC_PATH", str(compiler))

    assert build.find_iscc() == compiler.resolve()


def test_find_makeappx_usa_caminho_configurado(monkeypatch, tmp_path: Path):
    packager = tmp_path / "makeappx.exe"
    packager.write_bytes(b"packager")
    monkeypatch.setenv("MAKEAPPX_PATH", str(packager))

    assert build.find_makeappx() == packager.resolve()


def test_msix_version_reserva_quarto_campo_para_store():
    assert build.msix_version("2.7.15") == "2.7.15.0"
    assert build.msix_version("0.2.2") == "1.2.2.0"


@pytest.mark.parametrize("version", ["1.beta.0", "1.2.3.4", "65536.1"])
def test_msix_version_rejeita_valores_invalidos(version: str):
    with pytest.raises(ValueError):
        build.msix_version(version)


def test_render_msix_manifest_usa_identidade_da_store(tmp_path: Path):
    manifest = build.render_msix_manifest(tmp_path / "AppxManifest.xml")
    content = manifest.read_text(encoding="utf-8")

    assert build.STORE_PACKAGE_NAME in content
    assert build.STORE_PUBLISHER in content
    assert f'Version="{build.msix_version(build.__version__)}"' in content
    assert 'Executable="WhisperTranscriber.exe"' in content
    assert 'Name="runFullTrust"' in content


def test_generate_msix_assets_cria_dimensoes_obrigatorias(tmp_path: Path):
    from PIL import Image

    generated = build.generate_msix_assets(tmp_path)
    dimensions = {}
    for asset in generated:
        with Image.open(asset) as image:
            dimensions[asset.name] = image.size

    assert dimensions == {
        "Square44x44Logo.png": (44, 44),
        "Square150x150Logo.png": (150, 150),
        "StoreLogo.png": (50, 50),
    }


def test_verify_msix_confere_conteudo_sem_extrair(tmp_path: Path):
    manifest = build.render_msix_manifest(tmp_path / "AppxManifest.xml")
    package = tmp_path / "app.msix"
    with zipfile.ZipFile(package, "w") as archive:
        archive.write(manifest, "AppxManifest.xml")
        archive.writestr("WhisperTranscriber.exe", b"app")

    result = build.verify_msix(package)

    assert result == {
        "Name": build.STORE_PACKAGE_NAME,
        "Publisher": build.STORE_PUBLISHER,
        "Version": build.msix_version(build.__version__),
        "ProcessorArchitecture": "x64",
    }


def test_verify_executable_le_json_windowed(monkeypatch, tmp_path: Path):
    executable = tmp_path / "WhisperTranscriber.exe"
    executable.write_bytes(b"app")

    def fake_run(command, **_kwargs):
        output = Path(command[command.index("--self-check-output") + 1])
        output.write_text(
            json.dumps({"status": "ok", "dispositivo": "GPU CUDA: teste"}),
            encoding="utf-8",
        )

    monkeypatch.setattr(build.subprocess, "run", fake_run)

    result = build.verify_executable(executable, require_cuda=True)

    assert result["status"] == "ok"


def test_verify_executable_rejeita_build_cpu_quando_cuda_e_obrigatoria(
    monkeypatch, tmp_path: Path
):
    executable = tmp_path / "WhisperTranscriber.exe"
    executable.write_bytes(b"app")

    def fake_run(command, **_kwargs):
        output = Path(command[command.index("--self-check-output") + 1])
        output.write_text(
            json.dumps({"status": "ok", "dispositivo": "CPU (CUDA não disponível)"}),
            encoding="utf-8",
        )

    monkeypatch.setattr(build.subprocess, "run", fake_run)

    with pytest.raises(RuntimeError, match="deveria usar CUDA"):
        build.verify_executable(executable, require_cuda=True)


def test_verify_executable_pode_continuar_se_smart_app_control_bloquear(
    monkeypatch, tmp_path: Path
):
    executable = tmp_path / "WhisperTranscriber.exe"
    executable.touch()
    error = OSError("bloqueado")
    error.winerror = 4551

    def fake_run(*_args, **_kwargs):
        raise error

    monkeypatch.setattr(build.subprocess, "run", fake_run)

    result = build.verify_executable(
        executable, require_cuda=True, allow_policy_block=True
    )

    assert result["status"] == "bloqueado_politica"
