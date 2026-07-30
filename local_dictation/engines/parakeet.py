"""NVIDIA Parakeet via parakeet-mlx — fastest engine on Apple Silicon.

Feeds captured audio directly into the mel + generate path, skipping the
library's file loader (which would require FFmpeg).
"""

import numpy as np

from .base import Engine

MODEL_REPO = "mlx-community/parakeet-tdt-0.6b-v2"


class ParakeetEngine(Engine):
    name = "parakeet"

    def __init__(self):
        self._model = None

    def load(self):
        if self._model is None:
            from parakeet_mlx import from_pretrained

            self._model = from_pretrained(MODEL_REPO)
            # Metal compiles each op's kernel on first use (measured ~2s);
            # without this, that cost lands on the user's first real
            # dictation instead of here at startup.
            self._run(np.zeros(1600, dtype=np.float32))

    def _run(self, audio: np.ndarray) -> str:
        import mlx.core as mx
        from parakeet_mlx.audio import get_logmel

        mel = get_logmel(mx.array(audio), self._model.preprocessor_config)
        result = self._model.generate(mel)[0]
        return result.text.strip()

    def transcribe(self, audio: np.ndarray) -> str:
        self.load()
        return self._run(audio)
