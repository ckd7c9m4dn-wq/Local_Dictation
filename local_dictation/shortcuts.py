"""Whole-utterance shortcuts: a short spoken phrase expands to canned text.

When an entire dictation is *only* a configured shortcut phrase (ignoring
case, surrounding whitespace, and leading/trailing punctuation), the whole
transcript is replaced by that shortcut's expansion. Useful for canned
prompts — saying just "humanize" can paste a full paragraph of prompt text,
including long-form structured content (markdown, code, Obsidian
[[wiki-links]], numbered lists) with its formatting intact.

Each shortcut is delimited by an explicit "@shortcut: <phrase>" line and a
matching "@end" line:

    @shortcut: humanize
    Rewrite the following text to remove AI tells ...
    ... more lines ...
    @end

    @shortcut: summarize
    Summarize the following in three bullet points.
    @end

A shortcut can list several trigger phrases — comma-separated aliases that
all map to the same expansion, useful for covering how ASR is likely to
mis-hear a phrase (e.g. a mis-transcribed or misspelled variant):

    @shortcut: output to obsidian, output to obsidion
    Convert the attached meeting transcript into a single Obsidian note ...
    @end

Everything between the two markers is passed through byte-for-byte as the
expansion — blank lines, "#" comments, "[...]"/"[[...]]" links, indentation,
whatever the pasted content contains. "#" is only treated as a comment
marker outside of a shortcut block; a matching "@end" is the only thing that
closes one, so structured content can't accidentally terminate a block
early or get mistaken for a new phrase header. A block left open at end of
file is closed implicitly.
"""

import re

from .config import CONFIG_DIR

SHORTCUTS_PATH = CONFIG_DIR / "shortcuts.txt"

_START_RE = re.compile(r"^@shortcut:\s*(.+?)\s*$")
_END_RE = re.compile(r"^@end\s*$")

DEFAULT_SHORTCUTS = """\
# Whole-utterance shortcuts for canned prompts/snippets. Say ONLY one of the
# phrases named on an "@shortcut:" line and the entire dictation is replaced
# by everything up to the matching "@end" line — any content in between
# (blank lines, "#" comments, markdown, code, [[wiki links]]) is kept
# verbatim. List several comma-separated phrases on one "@shortcut:" line
# to give a shortcut multiple aliases that all trigger the same expansion
# (handy for covering ASR mis-transcriptions of the phrase).
#
# Matching ignores case, surrounding spaces, and trailing punctuation, and
# only fires when the phrase is the whole utterance — "humanize" alone
# triggers it; "humanize this paragraph" does not.
#
# Remove the leading "# " from the block below to enable it:
#
# @shortcut: humanize
# Rewrite the following text to sound natural and human. Remove common AI
# tells: hedging, over-qualification, repetitive sentence structure, and
# stock phrases like "it's important to note" or "in today's world". Keep
# the meaning, facts, and any specifics unchanged.
# @end
"""


def _normalize(phrase: str) -> str:
    """Lowercase, collapse whitespace, and strip surrounding punctuation."""
    phrase = re.sub(r"\s+", " ", phrase.strip().lower())
    return phrase.strip(".,!?;:\"'").strip()


def ensure_shortcuts_file() -> None:
    """Create the editable shortcuts file with example content if missing."""
    if not SHORTCUTS_PATH.exists():
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        SHORTCUTS_PATH.write_text(DEFAULT_SHORTCUTS)


def _parse_blocks() -> list[tuple[list[str], str]]:
    """Parse the file into ordered (alias keys, expansion) blocks.

    A block's "@shortcut:" line may list several comma-separated phrases —
    aliases that all trigger the same expansion.
    """
    try:
        text = SHORTCUTS_PATH.read_text()
    except OSError:
        return []

    blocks: list[tuple[list[str], str]] = []
    keys: list[str] = []
    buffer: list[str] = []

    def close():
        if keys:
            expansion = "\n".join(buffer).strip("\n")
            if expansion:
                blocks.append((keys, expansion))

    for line in text.splitlines():
        if not keys:
            if line.strip().startswith("#"):
                continue
            start = _START_RE.match(line)
            if start:
                keys = [k for k in (_normalize(p) for p in start.group(1).split(",")) if k]
                buffer = []
            # else: stray content outside any block — ignored
        elif _END_RE.match(line):
            close()
            keys, buffer = [], []
        else:
            buffer.append(line)
    close()  # tolerate a missing trailing "@end"

    return blocks


def get_shortcuts() -> dict[str, str]:
    """Flatten into {normalized phrase: expansion text}, one entry per alias."""
    shortcuts: dict[str, str] = {}
    for keys, expansion in _parse_blocks():
        for key in keys:
            shortcuts[key] = expansion
    return shortcuts


def list_phrases() -> list[str]:
    """One phrase per shortcut — its first alias — for display purposes."""
    return [keys[0] for keys, _ in _parse_blocks()]


def expand(text: str) -> str | None:
    """Return the expansion if the whole utterance is a shortcut, else None."""
    key = _normalize(text)
    if not key:
        return None
    return get_shortcuts().get(key)
