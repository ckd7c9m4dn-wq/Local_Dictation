"""Persistent JSON config in ~/.config/local_dictation/config.json."""

import json
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "local_dictation"
CONFIG_PATH = CONFIG_DIR / "config.json"

DEFAULTS = {
    "engine": "parakeet",  # "parakeet" | "whisper"
    "cleanup_enabled": True,
    "ollama_model": "qwen3:4b-instruct",
    "ollama_url": "http://localhost:11434",
    "hotkey": "alt_r",  # hold Right Option to talk (cleaned output)
    "verbatim_hotkey": "cmd_r",  # hold Right Command for raw, no-cleanup output
    "history_enabled": True,
    "trailing_space": False,
    "whisper_auto_language": False,  # False = locked to English (faster)
}


class Config:
    def __init__(self):
        self._data = dict(DEFAULTS)
        if CONFIG_PATH.exists():
            try:
                self._data.update(json.loads(CONFIG_PATH.read_text()))
            except (json.JSONDecodeError, OSError):
                pass

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = value
        self.save()

    def save(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(json.dumps(self._data, indent=2))
