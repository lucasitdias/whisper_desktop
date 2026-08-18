"""Formatação e persistência segura da transcrição em Markdown."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from .transcriber import TranscriptionResult


class MarkdownExporter:
    """Transforma um resultado de transcrição em um relatório Markdown."""

    @staticmethod
    def format_timestamp(seconds: float) -> str:
        total = max(0, int(seconds + 0.5))
        hours, remainder = divmod(total, 3600)
        minutes, secs = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    @staticmethod
    def _inline_code(value: str) -> str:
        return value.replace("`", "ˋ")

    @classmethod
    def render(cls, result: TranscriptionResult) -> str:
        source_name = Path(result.source_name).name
        title = Path(source_name).stem.replace("#", "\\#")
        date = result.transcribed_at.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
        processing = "GPU (CUDA)" if result.device == "cuda" else "CPU"
        lines = [
            f"# Transcrição de Áudio - {title}",
            "",
            f"- **Data da Transcrição:** {date}",
            f"- **Arquivo de Origem:** `{cls._inline_code(source_name)}`",
            f"- **Duração do Áudio:** {cls.format_timestamp(result.duration_seconds)}",
            f"- **Modelo Utilizado:** Whisper `{result.model_name}` (809M parâmetros)",
            f"- **Idioma Configurado:** Português do Brasil (`{result.language}`)",
            f"- **Processamento:** {processing}",
            "",
            "---",
            "",
            "## 📝 Transcrição Completa",
            "",
            result.text.strip() or "_Nenhuma fala foi identificada no arquivo._",
            "",
            "---",
            "",
            "## ⏱️ Transcrição com Marcadores Temporais (Timestamps)",
            "",
        ]
        segments = [segment for segment in result.segments if segment.text.strip()]
        if segments:
            for segment in segments:
                start = cls.format_timestamp(segment.start)
                end = cls.format_timestamp(segment.end)
                lines.append(f"- **[{start} -> {end}]** {segment.text.strip()}")
        else:
            lines.append("_Nenhum segmento com fala foi identificado._")
        return "\n".join(lines).rstrip() + "\n"

    @staticmethod
    def save(markdown: str, destination: str | Path) -> Path:
        """Grava UTF-8 de forma atômica no diretório de destino."""

        target = Path(destination).expanduser()
        if target.suffix.lower() != ".md":
            target = target.with_suffix(".md")
        target.parent.mkdir(parents=True, exist_ok=True)
        temp_name: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="\n",
                dir=target.parent,
                prefix=f".{target.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary:
                temporary.write(markdown)
                temporary.flush()
                os.fsync(temporary.fileno())
                temp_name = temporary.name
            os.replace(temp_name, target)
        except Exception:
            if temp_name:
                Path(temp_name).unlink(missing_ok=True)
            raise
        return target.resolve()
