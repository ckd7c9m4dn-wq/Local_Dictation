"""Terminology list that guides the AI cleanup stage.

Mirrors replacements.py's editable-file pattern: terms live in
~/.config/local_dictation/vocabulary.txt so they can be edited freely
(changes apply to the very next dictation — no restart needed).

Unlike replacements.txt (a mechanical, post-cleanup find/replace), these
terms are injected into the cleanup system prompt so the local model knows
the correct spelling of names, jargon, and product names it would
otherwise mangle — e.g. nudging a mis-heard "clod" back to "Claude". The
model still only uses them where the speaker clearly meant them; it never
inserts a term that wasn't said.
"""

from .config import CONFIG_DIR

VOCABULARY_PATH = CONFIG_DIR / "vocabulary.txt"

DEFAULT_VOCABULARY = """\
# One term or phrase per line — names, jargon, product names, acronyms.
# The AI cleanup stage uses these to correct mis-transcriptions and keep
# consistent spelling and capitalization. Lines starting with # are ignored.
# Claude
# Ollama
# Parakeet
"""


def ensure_vocabulary_file() -> None:
    """Create the editable vocabulary file with example content if missing."""
    if not VOCABULARY_PATH.exists():
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        VOCABULARY_PATH.write_text(DEFAULT_VOCABULARY)


def get_vocabulary() -> list[str]:
    """Parse one-term-per-line entries from the vocabulary file."""
    try:
        lines = VOCABULARY_PATH.read_text().splitlines()
    except OSError:
        return []
    terms = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        terms.append(line)
    return terms
