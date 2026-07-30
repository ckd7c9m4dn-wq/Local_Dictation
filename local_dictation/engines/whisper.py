"""OpenAI Whisper large-v3-turbo via mlx-whisper — 99-language coverage."""

import numpy as np

from .base import Engine

MODEL_REPO = "mlx-community/whisper-large-v3-turbo"


class WhisperEngine(Engine):
    name = "whisper"

    def __init__(self):
        self._loaded = False
        # None = auto-detect language (~1.1s slower per dictation: an extra
        # forward pass to guess the language before decoding). Locked to a
        # fixed language by default; app.py syncs this from config before
        # each transcribe() call.
        self.language = "en"

    def load(self):
        if not self._loaded:
            # Warm the weights cache with a tiny silent clip.
            self._run(np.zeros(1600, dtype=np.float32))
            self._loaded = True

    def _run(self, audio: np.ndarray) -> str:
        import mlx_whisper

        # temperature=0.0 forces a single decode pass. The mlx_whisper
        # default retries at up to 6 temperatures whenever it's not
        # confident (quiet audio, background noise, short utterances),
        # which measured 11+ seconds on ambiguous audio vs ~1s for one pass.
        result = mlx_whisper.transcribe(
            audio, path_or_hf_repo=MODEL_REPO, temperature=0.0, language=self.language
        )
        return result["text"].strip()

    def transcribe(self, audio: np.ndarray) -> str:
        text = self._run(audio)
        self._loaded = True
        return text
