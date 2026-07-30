"""Microphone capture: 16 kHz mono, suitable for both ASR engines."""

import threading

import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16_000


class Recorder:
    """Push-to-talk recorder. start() begins capture, stop() returns audio."""

    def __init__(self):
        self._chunks: list[np.ndarray] = []
        self._stream: sd.InputStream | None = None
        self._lock = threading.Lock()

    def start(self):
        with self._lock:
            if self._stream is not None:
                return
            self._chunks = []
            self._stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="float32",
                callback=self._on_audio,
            )
            self._stream.start()

    def _on_audio(self, indata, frames, time_info, status):
        self._chunks.append(indata.copy())

    def stop(self) -> np.ndarray:
        """Stop capture and return the recording as float32 mono at 16 kHz."""
        with self._lock:
            if self._stream is None:
                return np.zeros(0, dtype=np.float32)
            self._stream.stop()
            self._stream.close()
            self._stream = None
            if not self._chunks:
                return np.zeros(0, dtype=np.float32)
            return np.concatenate(self._chunks).flatten()

    @property
    def recording(self) -> bool:
        return self._stream is not None
