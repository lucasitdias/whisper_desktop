import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_metadados_usam_readme_da_raiz():
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert metadata["project"]["readme"] == "README.md"
    assert (ROOT / metadata["project"]["readme"]).is_file()


def test_metadados_identificam_autor_e_licenca():
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert metadata["project"]["authors"] == [{"name": "Lucas Dias"}]
    assert metadata["project"]["license"] == "MIT"
    assert "Copyright (c) 2026 Lucas Dias" in (ROOT / "LICENSE").read_text(
        encoding="utf-8"
    )
    citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    assert 'given-names: "Lucas"' in citation
    assert 'family-names: "Dias"' in citation
    assert "version: 0.3.0" in citation


def test_instalador_inclui_aviso_de_terceiros_movido_para_docs():
    script = (ROOT / "installer" / "WhisperTranscriber.iss").read_text(
        encoding="utf-8-sig"
    )

    assert "docs\\THIRD_PARTY_NOTICES.md" in script
    assert (ROOT / "docs" / "THIRD_PARTY_NOTICES.md").is_file()
    assert 'Source: "{#RootDir}\\LICENSE"' in script


def test_build_inclui_licenca_e_avisos_nos_portateis():
    script = (ROOT / "build.py").read_text(encoding="utf-8")

    assert 'executable.parent / "LICENSE"' in script
    assert 'executable.parent / "THIRD_PARTY_NOTICES.md"' in script


def test_atalho_windows_aponta_para_o_produto_reservado_na_store():
    shortcut = (
        ROOT / "store" / "Instalar-WhisperTranscriber-Windows.url"
    ).read_text(encoding="utf-8")

    assert "https://apps.microsoft.com/detail/9PHWS6MM59BG" in shortcut


def test_release_publica_todas_as_opcoes_suportadas():
    workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(
        encoding="utf-8"
    )

    assert "WhisperTranscriber-Linux-x64" in workflow
    assert "WhisperTranscriber-Setup-Linux-x64.deb" in workflow
    assert "WhisperTranscriber-Setup-Windows-x64.exe" in workflow
    assert "WhisperTranscriber-Setup-Windows-x64-CPU.exe" in workflow
    assert "WhisperTranscriber-Windows-x64.zip" in workflow
    assert "WhisperTranscriber-Linux-x64.tar.gz" in workflow
    assert "WhisperTranscriber-Windows-x64.zip.part-*" in workflow
    assert 'split --bytes=1900M' in workflow
    assert "--installer" in workflow
    assert "--installer-cpu" in workflow
    assert "https://download.pytorch.org/whl/cu130" in workflow
    assert "Instalar, verificar e remover o instalador NVIDIA CUDA" in workflow
    assert "Instalar, verificar e remover o instalador CPU" in workflow
    assert "self-check-nvidia.json" in workflow
    assert "self-check-cpu.json" in workflow
    assert "dpkg --install" in workflow
    assert "dpkg --remove" in workflow
    assert "tomllib.load(open('pyproject.toml', 'rb'))" in workflow
    assert "pull_request:" in workflow
    assert "if: startsWith(github.ref, 'refs/tags/v')" in workflow
    assert "SHA256SUMS-Linux.txt" in workflow
    assert "SHA256SUMS-Windows-NVIDIA-CUDA.txt" in workflow
    assert "SHA256SUMS-Windows-CPU.txt" in workflow
    assert "Instalar-WhisperTranscriber-Windows.url" in workflow
    assert "https://apps.microsoft.com/detail/9PHWS6MM59BG" in workflow
    assert "WhisperTranscriber-Setup-Windows-x64-Offline.zip\n" not in workflow
    assert "WhisperTranscriber-Setup-Windows-x64-CPU-Offline.zip\n" not in workflow


def test_ci_usa_somente_nomes_neutros_de_branches():
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8"
    )

    assert '"agent/**"' not in workflow
    assert '"release/**"' in workflow


def test_manifesto_windows_declara_dpi_per_monitor_v2():
    manifest = (
        ROOT / "packaging" / "windows" / "WhisperTranscriber.exe.manifest"
    ).read_text(encoding="utf-8")

    assert "PerMonitorV2,PerMonitor" in manifest
    assert 'requestedExecutionLevel level="asInvoker"' in manifest
