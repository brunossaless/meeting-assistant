"""Transcrição via whisper.cpp (binário `whisper-cpp` do Homebrew)."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


def _binary_path() -> str:
    path = shutil.which("whisper-cli")
    if not path:
        raise RuntimeError("whisper-cli não encontrado no PATH. Rode scripts/setup.sh.")
    return path


def transcribe_wav(wav_path: Path, model_path: Path, language: str = "pt") -> list[dict]:
    if not wav_path.is_file():
        return []
    out_base = wav_path.with_suffix("")
    cmd = [
        _binary_path(),
        "-m", str(model_path),
        "-f", str(wav_path),
        "-l", language,
        "-oj",
        "-of", str(out_base),
        "-nt",
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)

    json_path = out_base.with_suffix(".json")
    with open(json_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    segments = []
    for item in data.get("transcription", []):
        text = item.get("text", "").strip()
        if not text:
            continue
        offsets = item.get("offsets", {})
        segments.append(
            {
                "start": offsets.get("from", 0) / 1000.0,
                "end": offsets.get("to", 0) / 1000.0,
                "text": text,
            }
        )
    return segments
