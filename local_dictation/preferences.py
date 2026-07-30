"""General preferences/context appended to the AI cleanup system prompt.

Mirrors vocabulary.py's editable-file pattern: free-form text lives in
~/.config/local_dictation/system_prompt.txt so it can be edited freely (changes
apply to the very next dictation — no restart needed). Unlike vocabulary.txt
(a list of specific terms/spellings), this is unstructured context about the
speaker's standing preferences — e.g. locale/currency conventions or how to
interpret spoken numbers — that the model should apply to every transcript.
"""

from .config import CONFIG_DIR

PREFERENCES_PATH = CONFIG_DIR / "system_prompt.txt"

DEFAULT_PREFERENCES = """\
# General context and preferences for the AI cleanup stage. Free-form text —
# write it as instructions to the model. Lines starting with # are ignored.
# Applies to every dictation, in addition to the cleanup rules and
# terminology list.
#
# Examples (remove the leading "# " to enable):
#
# I'm in the UK — use £ for monetary values unless another currency is stated.
# When you hear ordinal-sounding numbers like "fifth" or "third", write them
# as "5th" and "3rd".
"""


def ensure_preferences_file() -> None:
    """Create the editable preferences file with example content if missing."""
    if not PREFERENCES_PATH.exists():
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        PREFERENCES_PATH.write_text(DEFAULT_PREFERENCES)


def get_preferences() -> str:
    """Non-comment lines from the preferences file, joined back into text."""
    try:
        lines = PREFERENCES_PATH.read_text().splitlines()
    except OSError:
        return ""
    kept = [line for line in lines if line.strip() and not line.strip().startswith("#")]
    return "\n".join(kept).strip()
