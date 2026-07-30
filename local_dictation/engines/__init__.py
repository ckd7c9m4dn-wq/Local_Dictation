"""ASR engine registry."""

from .base import Engine


def get_engine(name: str) -> Engine:
    if name == "parakeet":
        from .parakeet import ParakeetEngine

        return ParakeetEngine()
    if name == "whisper":
        from .whisper import WhisperEngine

        return WhisperEngine()
    raise ValueError(f"unknown engine: {name}")
