"""Captura de áudio: microfone (Bruno) e dispositivo de sistema (BlackHole)."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Optional

import numpy as np
import sounddevice as sd
import soundfile as sf

SAMPLE_RATE = 16000


def list_devices() -> list[dict]:
    return list(sd.query_devices())


def find_device_index(name_substring: str) -> Optional[int]:
    for i, d in enumerate(sd.query_devices()):
        if name_substring.lower() in d["name"].lower() and d["max_input_channels"] > 0:
            return i
    return None


class StreamRecorder:
    """Um InputStream que sempre mede energia (RMS) e opcionalmente grava em wav."""

    def __init__(self, device_index: Optional[int], samplerate: int = SAMPLE_RATE, channels: int = 1):
        self.device_index = device_index
        self.samplerate = samplerate
        self.channels = channels
        self._stream: Optional[sd.InputStream] = None
        self._file: Optional[sf.SoundFile] = None
        self._lock = threading.Lock()
        self._rms = 0.0

    def _callback(self, indata, frames, time_info, status) -> None:
        with self._lock:
            self._rms = float(np.sqrt(np.mean(np.square(indata))))
            if self._file is not None:
                self._file.write(indata)

    def open(self) -> None:
        self._stream = sd.InputStream(
            device=self.device_index,
            samplerate=self.samplerate,
            channels=self.channels,
            callback=self._callback,
        )
        self._stream.start()

    def close(self) -> None:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    def get_rms(self) -> float:
        with self._lock:
            return self._rms

    def start_writing(self, path: Path) -> None:
        f = sf.SoundFile(
            str(path), mode="w", samplerate=self.samplerate, channels=self.channels, subtype="PCM_16"
        )
        with self._lock:
            self._file = f

    def stop_writing(self) -> None:
        with self._lock:
            f, self._file = self._file, None
        if f is not None:
            f.close()


class MicRecorder:
    """Abre um stream novo do microfone só enquanto uma reunião está sendo gravada."""

    def __init__(self, device_index: Optional[int] = None, samplerate: int = SAMPLE_RATE, channels: int = 1):
        self.device_index = device_index
        self.samplerate = samplerate
        self.channels = channels
        self._recorder: Optional[StreamRecorder] = None

    def start(self, path: Path) -> None:
        self._recorder = StreamRecorder(self.device_index, self.samplerate, self.channels)
        self._recorder.open()
        self._recorder.start_writing(path)

    def stop(self) -> None:
        if self._recorder is not None:
            self._recorder.stop_writing()
            self._recorder.close()
            self._recorder = None
