"""Intercala as transcrições do microfone e do áudio de sistema por timestamp."""

from __future__ import annotations


def merge_transcripts(
    mic_segments: list[dict],
    system_segments: list[dict],
    mic_speaker: str = "Bruno Sales",
    system_speaker: str = "Outros participantes",
) -> list[dict]:
    tagged = [{**s, "speaker": mic_speaker} for s in mic_segments] + [
        {**s, "speaker": system_speaker} for s in system_segments
    ]
    tagged.sort(key=lambda s: s["start"])
    return tagged


def format_transcript(segments: list[dict]) -> str:
    return "\n".join(f"{_format_ts(s['start'])} {s['speaker']}: {s['text']}" for s in segments)


def _format_ts(seconds: float) -> str:
    total = int(seconds)
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"
