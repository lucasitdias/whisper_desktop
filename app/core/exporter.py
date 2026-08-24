"""Formatação e persistência segura da transcrição em Markdown."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from .transcriber import TranscriptionResult

MODEL_PARAMETER_LABELS = {
    "tiny": "39M parâmetros",
    "base": "74M parâmetros",
    "small": "244M parâmetros",
    "medium": "769M parâmetros",
    "large-v3": "1.550M parâmetros",
    "turbo": "809M parâmetros",
}


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
        processing = {
            "cuda": "GPU NVIDIA (CUDA)",
            "rocm": "GPU AMD (ROCm)",
            "xpu": "GPU Intel (XPU)",
            "cpu": "CPU",
        }.get(result.device, result.device.upper())
        coverage = result.processing_coverage_percent
        processed = cls.format_timestamp(result.processed_seconds)
        last_speech = result.last_speech_end_seconds
        confidence = (
            f"{result.average_word_confidence * 100:.1f}% em {result.word_count} palavras "
            f"({result.low_confidence_word_count} abaixo de 50%)"
            if result.average_word_confidence is not None
            else "indisponível"
        )
        lines = [
            f"# Transcrição de Áudio - {title}",
            "",
            f"- **Data da Transcrição:** {date}",
            f"- **Arquivo de Origem:** `{cls._inline_code(source_name)}`",
            f"- **Duração do Áudio:** {cls.format_timestamp(result.duration_seconds)}",
            (
                f"- **Modelo Utilizado:** Whisper `{result.model_name}` "
                f"({MODEL_PARAMETER_LABELS.get(result.model_name, 'quantidade não catalogada')})"
            ),
            f"- **Idioma Configurado:** Português do Brasil (`{result.language}`)",
            f"- **Processamento:** {processing}",
            (
                "- **Tempo de Processamento:** "
                f"{cls.format_timestamp(result.processing_seconds)}"
                if result.processing_seconds is not None
                else "- **Tempo de Processamento:** não medido"
            ),
            f"- **Cobertura do Processamento:** {coverage:.0f}% ({processed} decodificados)",
            f"- **Confiança Média Estimada:** {confidence}",
            f"- **Segmentos Revisados Automaticamente:** {result.reviewed_segment_count}",
            f"- **Possíveis Alucinações para Revisão:** {result.suspected_hallucination_count}",
            (
                "- **Hipóteses Descartadas sobre Silêncio Efetivo:** "
                f"{result.discarded_silence_segment_count}"
            ),
            (
                f"- **Última Fala Detectada:** {cls.format_timestamp(last_speech)}"
                if last_speech is not None
                else "- **Última Fala Detectada:** nenhuma fala identificada"
            ),
            "",
            "---",
            "",
            "## ✅ Verificação de Integridade",
            "",
            (
                f"O Whisper concluiu o processamento de {processed}, equivalente a "
                f"{coverage:.0f}% do áudio decodificado."
            ),
            "",
            (
                "> A cobertura confirma que o arquivo inteiro foi processado, mas a confiança é "
                "uma estimativa e não garante fidelidade palavra por palavra. Revise o áudio em "
                "conteúdos críticos."
            ),
            "",
            "### Palavras para revisão",
            "",
        ]
        if result.recording_device:
            lines.extend(
                [
                    "### Origem da gravação",
                    "",
                    f"- **Microfone:** {result.recording_device}",
                    f"- **Formato salvo:** {result.recording_format or 'não informado'}",
                    (
                        f"- **Pico capturado:** {result.recording_peak_dbfs:.1f} dBFS"
                        if result.recording_peak_dbfs is not None
                        else "- **Pico capturado:** sem sinal mensurável"
                    ),
                    "",
                ]
            )
            if result.recording_warnings:
                lines.extend(["> " + warning for warning in result.recording_warnings])
                lines.append("")
        if result.low_confidence_words:
            for word in result.low_confidence_words:
                timestamp = cls.format_timestamp(word.start)
                safe_word = cls._inline_code(word.text) or "(sem texto)"
                lines.append(
                    f"- **[[{timestamp}](audio://seek/{word.start:.3f})]** `{safe_word}` — "
                    f"confiança {word.probability * 100:.1f}%"
                )
        else:
            lines.append("_Nenhuma palavra ficou abaixo do limiar de confiança de 50%._")
        lines.extend(
            [
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
        )
        segments = [segment for segment in result.segments if segment.text.strip()]
        if segments:
            for segment in segments:
                start = cls.format_timestamp(segment.start)
                end = cls.format_timestamp(segment.end)
                flags = []
                if segment.reviewed:
                    flags.append("revisão automática")
                if segment.suspected_hallucination:
                    flags.append("⚠ possível alucinação")
                review = f" — _{' | '.join(flags)}_" if flags else ""
                lines.append(
                    f"- **[[{start}](audio://seek/{segment.start:.3f}) -> {end}]** "
                    f"{segment.text.strip()}{review}"
                )
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
