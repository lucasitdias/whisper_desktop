from datetime import UTC, datetime
from pathlib import Path

from app.core.exporter import MarkdownExporter
from app.core.transcriber import (
    TranscriptionResult,
    TranscriptionSegment,
    TranscriptionWord,
)


def make_result(**overrides):
    values = {
        "source_name": "reunião.m4a",
        "duration_seconds": 3661.4,
        "processed_seconds": 3661.4,
        "text": "Olá, mundo.",
        "segments": (TranscriptionSegment(0, 5.2, "Olá, mundo."),),
        "model_name": "turbo",
        "language": "pt",
        "device": "cuda",
        "transcribed_at": datetime(2026, 8, 18, 10, 30, tzinfo=UTC),
        "average_word_confidence": 0.937,
        "word_count": 2,
        "low_confidence_words": (TranscriptionWord(4.2, 4.8, "mundo", 0.42),),
    }
    values.update(overrides)
    return TranscriptionResult(**values)


def test_renderiza_metadados_unicode_e_timestamp_superior_a_uma_hora():
    markdown = MarkdownExporter.render(make_result())
    assert "# Transcrição de Áudio - reunião" in markdown
    assert "`reunião.m4a`" in markdown
    assert "01:01:01" in markdown
    assert "GPU NVIDIA (CUDA)" in markdown


def test_renderiza_backend_amd_rocm():
    markdown = MarkdownExporter.render(make_result(device="rocm"))
    assert "GPU AMD (ROCm)" in markdown


def test_renderiza_backend_intel_xpu():
    markdown = MarkdownExporter.render(make_result(device="xpu"))
    assert "GPU Intel (XPU)" in markdown
    assert "Cobertura do Processamento:** 100%" in markdown
    assert "Confiança Média Estimada:** 93.7%" in markdown
    assert "não garante fidelidade palavra por palavra" in markdown
    assert "`mundo` — confiança 42.0%" in markdown
    assert "**[00:00:00 -> 00:00:05]** Olá, mundo." in markdown


def test_renderiza_resultado_sem_fala():
    markdown = MarkdownExporter.render(make_result(text="", segments=()))
    assert "Nenhuma fala foi identificada" in markdown
    assert "Nenhum segmento com fala" in markdown


def test_salva_em_utf8_e_adiciona_extensao(tmp_path: Path):
    destination = MarkdownExporter.save("# Olá\n", tmp_path / "resultado")
    assert destination.name == "resultado.md"
    assert destination.read_text(encoding="utf-8") == "# Olá\n"
    assert not list(tmp_path.glob("*.tmp"))
