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
    assert build.msix_version("0.2.1") == "1.2.1.0"


@pytest.mark.parametrize("version", ["1.beta.0", "1.2.3.4", "65536.1"])
def test_msix_version_rejeita_valores_invalidos(version: str):
    with pytest.raises(ValueError):
        build.msix_version(version)


def test_render_msix_manifest_usa_identidade_da_store(tmp_path: Path):
    manifest = build.render_msix_manifest(tmp_path / "AppxManifest.xml")
    content = manifest.read_text(encoding="utf-8")

    assert build.STORE_PACKAGE_NAME in content
    assert build.STORE_PUBLISHER in content
    assert "<PublisherDisplayName>Lucas Dias</PublisherDisplayName>" in content
    assert f'Version="{build.STORE_PACKAGE_VERSION}"' in content
    assert 'Executable="WhisperTranscriber.exe"' in content
    assert 'Name="runFullTrust"' in content


def test_licenca_de_distribuicao_esta_disponivel():
    license_file = build._license_file()

    assert license_file.name == "LICENSE"
    assert "Copyright (c) 2026 Lucas Dias" in license_file.read_text(encoding="utf-8")


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
        "Version": build.STORE_PACKAGE_VERSION,
        "ProcessorArchitecture": "x64",
    }


def test_verify_executable_le_json_windowed(monkeypatch, tmp_path: Path):
    executable = tmp_path / "WhisperTranscriber.exe"
    executable.write_bytes(b"app")

    def fake_run(command, **_kwargs):
        output = Path(command[command.index("--self-check-output") + 1])
        output.write_text(
            json.dumps(
                {
                    "status": "ok",
                    "dispositivo": "GPU NVIDIA CUDA: GPU de teste",
                    "runtime_pytorch": "NVIDIA CUDA 13.0",
                    "modelos_offline": {
                        "medium": "bundled",
                        "turbo": "bundled",
                    },
                }
            ),
            encoding="utf-8",
        )

    monkeypatch.setattr(build.subprocess, "run", fake_run)

    result = build.verify_executable(
        executable, require_cuda=True, require_runtime="NVIDIA CUDA"
    )

    assert result["status"] == "ok"


def test_verify_executable_rejeita_runtime_incorreto(monkeypatch, tmp_path: Path):
    executable = tmp_path / "WhisperTranscriber.exe"
    executable.write_bytes(b"app")

    def fake_run(command, **_kwargs):
        output = Path(command[command.index("--self-check-output") + 1])
        output.write_text(
            json.dumps(
                {
                    "status": "ok",
                    "dispositivo": "CPU (aceleração por GPU não disponível)",
                    "runtime_pytorch": "CPU",
                    "modelos_offline": {
                        "medium": "bundled",
                        "turbo": "bundled",
                    },
                }
            ),
            encoding="utf-8",
        )

    monkeypatch.setattr(build.subprocess, "run", fake_run)

    with pytest.raises(RuntimeError, match="deveria conter o runtime NVIDIA CUDA"):
        build.verify_executable(executable, require_runtime="NVIDIA CUDA")


def test_verify_executable_rejeita_build_cpu_quando_cuda_e_obrigatoria(
    monkeypatch, tmp_path: Path
):
    executable = tmp_path / "WhisperTranscriber.exe"
    executable.write_bytes(b"app")

    def fake_run(command, **_kwargs):
        output = Path(command[command.index("--self-check-output") + 1])
        output.write_text(
            json.dumps(
                {
                    "status": "ok",
                    "dispositivo": "CPU (CUDA não disponível)",
                    "modelos_offline": {
                        "medium": "bundled",
                        "turbo": "bundled",
                    },
                }
            ),
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


def test_nomes_dos_instaladores_separam_cuda_e_cpu():
    assert build.INSTALLER_NAME == "WhisperTranscriber-Setup-Windows-x64.exe"
    assert build.CPU_INSTALLER_NAME == "WhisperTranscriber-Setup-Windows-x64-CPU.exe"
    assert build.WINDOWS_PORTABLE_NAME.endswith(".zip")
    assert build.LINUX_PORTABLE_NAME.endswith(".tar.gz")
    assert build.CUDA_INSTALLER_BUNDLE_NAME.endswith("-Offline.zip")
    assert build.CPU_INSTALLER_BUNDLE_NAME.endswith("-Offline.zip")


def test_fatias_cuda_e_cpu_nao_se_misturam(tmp_path: Path):
    cuda = tmp_path / build.INSTALLER_NAME
    cpu = tmp_path / build.CPU_INSTALLER_NAME
    for name in (
        f"{cuda.stem}-1.bin",
        f"{cuda.stem}-2.bin",
        f"{cpu.stem}-1.bin",
        f"{cpu.stem}-2.bin",
        f"{cuda.stem}-anexo.bin",
    ):
        (tmp_path / name).touch()

    assert [path.name for path in build.installer_slices(cuda)] == [
        f"{cuda.stem}-1.bin",
        f"{cuda.stem}-2.bin",
    ]
    assert [path.name for path in build.installer_slices(cpu)] == [
        f"{cpu.stem}-1.bin",
        f"{cpu.stem}-2.bin",
    ]


def test_metadados_de_distribuicao_identificam_o_desenvolvedor():
    assert build.STORE_PUBLISHER_DISPLAY_NAME == "Lucas Dias"
    assert build.STORE_PACKAGE_VERSION == "1.3.4.0"
