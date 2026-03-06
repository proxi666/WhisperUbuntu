#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from faster_whisper import WhisperModel


def choose_compute_type(device: str, requested: str | None) -> str:
    if requested:
        return requested

    if device == "cuda":
        return "float16"

    return "int8"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Transcribe audio locally with faster-whisper."
    )
    parser.add_argument("audio", type=Path, help="Path to audio or video file")
    parser.add_argument(
        "--model",
        default="large-v3-turbo",
        help="Whisper model name (default: large-v3-turbo)",
    )
    parser.add_argument(
        "--device",
        default="auto",
        choices=["auto", "cuda", "cpu"],
        help="Inference device preference",
    )
    parser.add_argument(
        "--compute-type",
        default=None,
        help="Override compute type, e.g. float16 or int8_float16",
    )
    parser.add_argument(
        "--language",
        default="en",
        help="Language code. For Indian English, keep this as 'en'.",
    )
    parser.add_argument(
        "--beam-size",
        type=int,
        default=5,
        help="Beam size for decoding",
    )
    parser.add_argument(
        "--vad-filter",
        action="store_true",
        help="Enable VAD to skip silence",
    )
    parser.add_argument(
        "--word-timestamps",
        action="store_true",
        help="Include word-level timestamps in the JSON output",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output transcript text path",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=None,
        help="Output structured JSON path",
    )
    return parser


def resolve_device(preference: str) -> str:
    if preference != "auto":
        return preference

    nvidia_smi = shutil.which("nvidia-smi")
    if not nvidia_smi:
        return "cpu"

    try:
        result = subprocess.run(
            [nvidia_smi, "--query-gpu=name", "--format=csv,noheader"],
            check=False,
            capture_output=True,
            text=True,
        )
    except Exception:
        return "cpu"

    return "cuda" if result.returncode == 0 else "cpu"


def main() -> int:
    args = build_parser().parse_args()
    if not args.audio.exists():
        print(f"Audio file not found: {args.audio}", file=sys.stderr)
        return 1

    device = resolve_device(args.device)
    compute_type = choose_compute_type(device, args.compute_type)

    print(
        f"Loading model={args.model} device={device} compute_type={compute_type}",
        file=sys.stderr,
    )
    model = WhisperModel(args.model, device=device, compute_type=compute_type)

    segments, info = model.transcribe(
        str(args.audio),
        language=args.language,
        beam_size=args.beam_size,
        vad_filter=args.vad_filter,
        word_timestamps=args.word_timestamps,
    )

    text_parts: list[str] = []
    json_segments: list[dict[str, object]] = []

    for segment in segments:
        text_parts.append(segment.text.strip())
        segment_payload: dict[str, object] = {
            "start": segment.start,
            "end": segment.end,
            "text": segment.text.strip(),
        }
        if args.word_timestamps and getattr(segment, "words", None):
            segment_payload["words"] = [
                {
                    "start": word.start,
                    "end": word.end,
                    "word": word.word,
                    "probability": word.probability,
                }
                for word in segment.words
            ]
        json_segments.append(segment_payload)

    transcript = "\n".join(part for part in text_parts if part).strip() + "\n"

    if args.output:
        args.output.write_text(transcript, encoding="utf-8")
    else:
        sys.stdout.write(transcript)

    if args.json_output:
        payload = {
            "model": args.model,
            "device": device,
            "compute_type": compute_type,
            "language": args.language,
            "language_probability": info.language_probability,
            "duration": info.duration,
            "segments": json_segments,
        }
        args.json_output.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
