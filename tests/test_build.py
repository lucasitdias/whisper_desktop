import json
from pathlib import Path

import pytest

import build


def test_find_iscc_usa_caminho_configurado(monkeypatch, tmp_path: Path):
    compiler = tmp_path / "ISCC.exe"
    compiler.write_bytes(b"compiler")
    monkeypatch.setenv("ISCC_PATH", str(compiler))

    assert build.find_iscc() == compiler.resolve()


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
