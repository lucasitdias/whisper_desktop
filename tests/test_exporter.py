from datetime import UTC, datetime
from pathlib import Path

from app.core.exporter import MarkdownExporter
from app.core.transcriber import TranscriptionResult, TranscriptionSegment


def make_result(**overrides):
    values = {
        "source_name": "reunião.m4a",
        "duration_seconds": 3661.4,
        "text": "Olá, mundo.",
        "segments": (TranscriptionSegment(0, 5.2, "Olá, mundo."),),
        "model_name": "turbo",
        "language": "pt",
        "device": "cuda",
        "transcribed_at": datetime(2026, 8, 18, 10, 30, tzinfo=UTC),
    }
    values.update(overrides)
    return TranscriptionResult(**values)


def test_renderiza_metadados_unicode_e_timestamp_superior_a_uma_hora():
    markdown = MarkdownExporter.render(make_result())
    assert "# Transcrição de Áudio - reunião" in markdown
    assert "`reunião.m4a`" in markdown
    assert "01:01:01" in markdown
    assert "GPU (CUDA)" in markdown
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
