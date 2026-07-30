"""Find/replace list for standardizing recognized terms in transcripts.

Mirrors cleanup.py's editable-prompt pattern: pairs live in
~/.config/local_dictation/replacements.txt so they can be edited freely
(changes apply to the very next dictation — no restart needed).
"""

import re

from .config import CONFIG_DIR

REPLACEMENTS_PATH = CONFIG_DIR / "replacements.txt"

DEFAULT_REPLACEMENTS = """\
# One replacement per line: term -> standard term
# Matching is case-insensitive and whole-word. Lines starting with # are ignored.
# teh -> the
# gonna -> going to
"""


def ensure_replacements_file() -> None:
    """Create the editable replacements file with example content if missing."""
    if not REPLACEMENTS_PATH.exists():
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        REPLACEMENTS_PATH.write_text(DEFAULT_REPLACEMENTS)


def get_replacements() -> list[tuple[str, str]]:
    """Parse "term -> standard term" pairs from the replacements file."""
    try:
        lines = REPLACEMENTS_PATH.read_text().splitlines()
    except OSError:
        return []
    pairs = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        term, sep, standard = line.partition("->")
        if sep:
            term, standard = term.strip(), standard.strip()
            if term:
                pairs.append((term, standard))
    return pairs


def apply(text: str) -> str:
    """Replace each recognized term with its standard term, whole-word and case-insensitive."""
    for term, standard in get_replacements():
        text = re.sub(
            rf"\b{re.escape(term)}\b", standard, text, flags=re.IGNORECASE
        )
    return text
