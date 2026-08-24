"""Benchmark opt-in de WER/CER para áudios autorizados em Português do Brasil."""

from __future__ import annotations

import argparse
import json
import re
import time
import unicodedata
from pathlib import Path
from typing import Any

import whisper

from app.core.ffmpeg_finder import FFmpegFinder
from app.core.transcriber import (
    TranscriberWorker,
    TranscriptionOptions,
    TranscriptionPriority,
)


def normalize(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return " ".join(re.findall(r"[\wÀ-ÿ]+", normalized, flags=re.UNICODE))


def edit_distance(reference: list[str], hypothesis: list[str]) -> int:
    previous = list(range(len(hypothesis) + 1))
    for row, expected in enumerate(reference, start=1):
        current = [row]
        for column, actual in enumerate(hypothesis, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[column] + 1,
                    previous[column - 1] + (expected != actual),
                )
            )
        previous = current
    return previous[-1]


def error_rate(reference: str, hypothesis: str, *, characters: bool = False) -> float:
    expected_text = normalize(reference)
    actual_text = normalize(hypothesis)
    expected = list(expected_text) if characters else expected_text.split()
    actual = list(actual_text) if characters else actual_text.split()
    return edit_distance(expected, actual) / max(1, len(expected))


def load_manifest(path: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        entry = json.loads(line)
        audio = Path(entry["audio"])
        if not audio.is_absolute():
            audio = path.parent / audio
        if not audio.is_file() or not str(entry.get("reference", "")).strip():
            raise ValueError(f"Entrada inválida na linha {line_number} do manifesto.")
        entry["audio"] = audio.resolve()
        entries.append(entry)
    if not entries:
        raise ValueError("O manifesto não contém amostras válidas.")
    return entries


def benchmark(
    entries: list[dict[str, Any]],
    models: list[str],
    include_review: bool,
    priorities: list[str] | None = None,
) -> dict[str, Any]:
    ffmpeg = FFmpegFinder.ensure_available()
    FFmpegFinder.prepend_to_path(ffmpeg)
    device = TranscriberWorker.detect_device()
    selected_priorities = [
        TranscriptionPriority(priority)
        for priority in (priorities or [TranscriptionPriority.BALANCED.value])
    ]
    results: list[dict[str, Any]] = []
    for model_name in models:
        try:
            for priority in selected_priorities:
                review_modes = (
                    [False, True]
                    if include_review and priority is not TranscriptionPriority.MAX_FIDELITY
                    else [False]
                )
                for selective_review in review_modes:
                    for entry in entries:
                        audio = whisper.load_audio(str(entry["audio"]))
                        duration = float(len(audio) / whisper.audio.SAMPLE_RATE)
                        options = TranscriptionOptions(
                            model_name=model_name,
                            initial_prompt=str(entry.get("context", "")),
                            selective_review=selective_review,
                            priority=priority,
                        )
                        worker = TranscriberWorker(entry["audio"], options=options)
                        started = time.perf_counter()
                        sample_device = device
                        try:
                            raw = worker._transcribe(audio, duration, sample_device)
                        except Exception as error:
                            if sample_device == "cpu" or not worker._is_accelerator_oom(
                                error, sample_device
                            ):
                                raise
                            TranscriberWorker.release_cached_model()
                            sample_device = "cpu"
                            raw = worker._transcribe(audio, duration, sample_device)
                        hypothesis = str(raw.get("text", "")).strip()
                        reference = str(entry["reference"])
                        terms = [normalize(str(term)) for term in entry.get("terms", [])]
                        normalized_hypothesis = normalize(hypothesis)
                        results.append(
                            {
                                "audio": Path(entry["audio"]).name,
                                "model": model_name,
                                "priority": priority.value,
                                "selective_review": options.effective_selective_review,
                                "wer": error_rate(reference, hypothesis),
                                "cer": error_rate(
                                    reference, hypothesis, characters=True
                                ),
                                "term_accuracy": (
                                    sum(
                                        term in normalized_hypothesis for term in terms
                                    )
                                    / len(terms)
                                    if terms
                                    else None
                                ),
                                "elapsed_seconds": time.perf_counter() - started,
                                "device": sample_device,
                                "reference": reference,
                                "hypothesis": hypothesis,
                            }
                        )
        finally:
            TranscriberWorker.release_cached_model()
    return summarize(results, device)


def summarize(results: list[dict[str, Any]], device: str) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for result in results:
        key = (
            f"{result['model']}:{result['priority']}:"
            f"{'review' if result['selective_review'] else 'baseline'}"
        )
        groups.setdefault(key, []).append(result)
    summary = {}
    for key, samples in groups.items():
        term_values = [
            item["term_accuracy"]
            for item in samples
            if item["term_accuracy"] is not None
        ]
        summary[key] = {
            "samples": len(samples),
            "wer": sum(item["wer"] for item in samples) / len(samples),
            "cer": sum(item["cer"] for item in samples) / len(samples),
            "term_accuracy": sum(term_values) / len(term_values) if term_values else None,
            "elapsed_seconds": sum(item["elapsed_seconds"] for item in samples),
        }
    return {"device": device, "summary": summary, "samples": results}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="JSONL com audio, reference, context e terms")
    parser.add_argument("--models", nargs="+", default=["turbo", "large-v3"])
    parser.add_argument(
        "--priorities",
        nargs="+",
        choices=[priority.value for priority in TranscriptionPriority],
        default=[TranscriptionPriority.BALANCED.value],
    )
    parser.add_argument("--include-selective-review", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("benchmark-result.json"))
    args = parser.parse_args()
    report = benchmark(
        load_manifest(args.manifest),
        args.models,
        args.include_selective_review,
        args.priorities,
    )
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
