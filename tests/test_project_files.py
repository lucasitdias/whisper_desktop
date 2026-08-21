import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_metadados_usam_readme_da_raiz():
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert metadata["project"]["readme"] == "README.md"
    assert (ROOT / metadata["project"]["readme"]).is_file()


def test_instalador_inclui_aviso_de_terceiros_movido_para_docs():
    script = (ROOT / "installer" / "WhisperTranscriber.iss").read_text(
        encoding="utf-8-sig"
    )

    assert "docs\\THIRD_PARTY_NOTICES.md" in script
    assert (ROOT / "docs" / "THIRD_PARTY_NOTICES.md").is_file()


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
    assert "WhisperTranscriber-Windows-x64.exe" in workflow
    assert "--installer-cpu" in workflow
    assert "Instalar, verificar e remover o instalador offline" in workflow
    assert "self-check-instalado.json" in workflow
    assert "dpkg --install" in workflow
    assert "dpkg --remove" in workflow
    assert "tomllib.load(open('pyproject.toml', 'rb'))" in workflow
    assert "pull_request:" in workflow
    assert "if: startsWith(github.ref, 'refs/tags/v')" in workflow
    assert "SHA256SUMS-Linux.txt" in workflow
    assert "SHA256SUMS-Windows.txt" in workflow
    assert "Instalar-WhisperTranscriber-Windows.url" in workflow
    assert "https://apps.microsoft.com/detail/9PHWS6MM59BG" in workflow
