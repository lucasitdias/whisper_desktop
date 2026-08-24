"""Executa uma inferência curta usando somente checkpoints já disponíveis localmente."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from app.core.model_catalog import MODEL_BY_ID, ModelManager
from app.core.transcriber import (
    TranscriberWorker,
    TranscriptionOptions,
    TranscriptionResult,
)


def validate(audio: Path, model_id: str, *, force_cpu: bool = False) -> dict[str, object]:
    spec = MODEL_BY_ID[model_id]
    checkpoint = ModelManager.require_checkpoint(spec)
    results: list[TranscriptionResult] = []
    failures: list[str] = []
    devices: list[tuple[str, str]] = []
    worker = TranscriberWorker(
        audio,
        options=TranscriptionOptions(model_name=model_id),
        public_source_name=audio.name,
    )
    if force_cpu:
        worker.detect_device = lambda: "cpu"  # type: ignore[method-assign]
    worker.completed.connect(results.append)
    worker.failed.connect(failures.append)
    worker.cancelled.connect(failures.append)
    worker.device_detected.connect(lambda backend, text: devices.append((backend, text)))
    started = time.perf_counter()
    worker.run()
    elapsed = time.perf_counter() - started
    TranscriberWorker.release_cached_model()
    if failures or not results:
        raise RuntimeError(failures[-1] if failures else "A inferência não retornou resultado.")
    result = results[-1]
    return {
        "modelo": model_id,
        "checkpoint": str(checkpoint),
        "dispositivo": devices[-1][1] if devices else result.device,
        "duracao_audio_s": round(result.duration_seconds, 3),
        "tempo_s": round(elapsed, 3),
        "cobertura_percentual": round(result.processing_coverage_percent, 2),
        "texto": result.text,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("audio", type=Path)
    parser.add_argument(
        "--models",
        nargs="+",
        choices=tuple(MODEL_BY_ID),
        default=["medium", "turbo", "large-v3"],
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--cpu", action="store_true", help="força o fallback CPU")
    args = parser.parse_args()
    payload = [
        validate(args.audio.resolve(), model_id, force_cpu=args.cpu)
        for model_id in args.models
    ]
    serialized = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(serialized, encoding="utf-8")
    print(serialized, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
