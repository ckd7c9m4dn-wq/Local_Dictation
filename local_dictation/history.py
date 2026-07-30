"""Append-only history of dictated text in ~/.config/local_dictation/history.txt."""

import datetime

from .config import CONFIG_DIR

HISTORY_PATH = CONFIG_DIR / "history.txt"


def append(text: str, engine: str, cleaned: bool):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    tag = f"{engine}, cleaned" if cleaned else engine
    with open(HISTORY_PATH, "a", encoding="utf-8") as f:
        f.write(f"[{stamp}] ({tag})\n{text}\n\n")


def ensure_file():
    if not HISTORY_PATH.exists():
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        HISTORY_PATH.touch()
