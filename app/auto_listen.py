"""Monitor de fundo: detecta início/fim de reunião pela energia do áudio de sistema."""

from __future__ import annotations

import threading
import time
from typing import Callable


class AutoListener:
    def __init__(
        self,
        monitor,
        threshold: float,
        start_seconds: float,
        stop_seconds: float,
        poll_interval: float,
        on_start: Callable[[], None],
        on_stop: Callable[[], None],
    ):
        self.monitor = monitor
        self.threshold = threshold
        self.start_seconds = start_seconds
        self.stop_seconds = stop_seconds
        self.poll_interval = poll_interval
        self.on_start = on_start
        self.on_stop = on_stop

        self._active = False
        self._manual = False
        self._sound_since: float | None = None
        self._silence_since: float | None = None
        self._stop_flag = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_flag.set()

    def notify_external_start(self) -> None:
        self._active = True
        self._manual = True
        self._silence_since = None

    def notify_external_stop(self) -> None:
        self._active = False
        self._manual = False
        self._sound_since = None

    def _run(self) -> None:
        while not self._stop_flag.is_set():
            time.sleep(self.poll_interval)
            is_sound = self.monitor.get_rms() > self.threshold
            now = time.monotonic()

            if not self._active:
                if is_sound:
                    self._sound_since = self._sound_since or now
                    if now - self._sound_since >= self.start_seconds:
                        self._sound_since = None
                        self._active = True
                        self._manual = False
                        try:
                            self.on_start()
                        except Exception:
                            self._active = False
                else:
                    self._sound_since = None
            elif not self._manual:
                if not is_sound:
                    self._silence_since = self._silence_since or now
                    if now - self._silence_since >= self.stop_seconds:
                        self._silence_since = None
                        self._active = False
                        try:
                            self.on_stop()
                        except Exception:
                            pass
                else:
                    self._silence_since = None
