"""Engine interface: load once, transcribe 16 kHz float32 mono audio."""

import tempfile
from abc import ABC, abstractmethod

import numpy as np
import soundfile as sf

from ..audio import SAMPLE_RATE


class Engine(ABC):
    name: str = "base"

    @abstractmethod
    def load(self):
        """Load model weights (idempotent; called once, kept warm)."""

    @abstractmethod
    def transcribe(self, audio: np.ndarray) -> str:
        """Transcribe float32 mono 16 kHz audio to text."""

    @staticmethod
    def _to_wav(audio: np.ndarray) -> str:
        """Write audio to a temp wav file, return its path."""
        f = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        sf.write(f.name, audio, SAMPLE_RATE)
        return f.name
